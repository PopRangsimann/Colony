"""
Recovery-Preserving Helper Selection
======================================
Selects helper nodes for collaborative processing while preserving
nodes critical for future recovery operations.

Implements Phase V — Step 2 (Eq. 36–38).

    RC_i     = ψ₁·FRI + ψ₂·RS                              (Eq. 36)
    HScore_i = λ₁·A + λ₂·RC - λ₃·L                         (Eq. 37)
    Reserve if RC_i >= τ_R                                   (Eq. 38)
"""

from __future__ import annotations

import sys
import os
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from phase4_load_balancing.fri import compute_fri
from phase4_load_balancing.state_replication import compute_recovery_score


def compute_recovery_capability(fog_node) -> float:
    """
    Eq. 36:  RC_i = ψ₁·FRI + ψ₂·RS

    Combined recovery capability score.
    """
    fri = compute_fri(fog_node)
    rs = compute_recovery_score(fog_node)
    return config.RC_PSI_1 * fri + config.RC_PSI_2 * rs


def compute_helper_score(
    available_capacity: float,
    recovery_capability: float,
    latency_norm: float,
) -> float:
    """
    Eq. 37:  HScore_i = λ₁·A + λ₂·RC - λ₃·L

    Helper node selection score (higher = better helper).

    Parameters
    ----------
    available_capacity : float
        Available computational capacity A_i (normalized).
    recovery_capability : float
        Recovery capability score RC_i.
    latency_norm : float
        Normalized communication latency L_i ∈ [0, 1].
    """
    return (
        config.HSCORE_LAMBDA_1 * available_capacity
        + config.HSCORE_LAMBDA_2 * recovery_capability
        - config.HSCORE_LAMBDA_3 * latency_norm
    )


def select_helpers(
    fog_nodes: list,
    hosting_node,
    delta_c: float,
    tau_r: float = None,
) -> Tuple[List, Dict[str, float]]:
    """
    Eq. 38:  Reserve if RC_i >= τ_R (when alternatives exist)

    Select helper nodes for collaborative resource assistance.
    Recovery-critical nodes (RC >= τ_R) are preferentially reserved
    when sufficient alternative helpers exist.

    Parameters
    ----------
    fog_nodes : list[FogNode]
        All fog nodes.
    hosting_node : FogNode
        The overloaded node requesting help.
    delta_c : float
        Resource deficit to fill.
    tau_r : float, optional
        Recovery capability threshold.

    Returns
    -------
    (selected_helpers, all_scores)
        List of selected helper nodes and dict of all HScores.
    """
    if tau_r is None:
        tau_r = config.TAU_R

    # Candidate helpers: alive, not the host, not MFN/SMFN
    candidates = [
        n for n in fog_nodes
        if n.is_alive
        and n.node_id != hosting_node.node_id
        and not n.is_mfn
        and not n.is_smfn
    ]

    if not candidates:
        # Fall back to any alive node except the host
        candidates = [
            n for n in fog_nodes
            if n.is_alive and n.node_id != hosting_node.node_id
        ]

    # Compute RC and HScore for each candidate
    scored = []
    all_scores = {}
    for node in candidates:
        rc = compute_recovery_capability(node)

        # Available capacity: CPU * (1 - queue occupancy)
        available = node.cpu * (1.0 - node.queue_occupancy)

        # Normalize latency
        lat_min, lat_max = config.LATENCY_RANGE
        lat_norm = (node.latency - lat_min) / max(lat_max - lat_min, 1e-6)
        lat_norm = max(0.0, min(1.0, lat_norm))

        hscore = compute_helper_score(available, rc, lat_norm)

        scored.append((node, hscore, rc, available))
        all_scores[node.node_id] = {
            "HScore": hscore,
            "RC": rc,
            "available": available,
        }

    # Sort by HScore descending
    scored.sort(key=lambda x: x[1], reverse=True)

    # Separate recovery-critical and normal helpers
    critical = [(n, h, rc, a) for n, h, rc, a in scored if rc >= tau_r]
    normal = [(n, h, rc, a) for n, h, rc, a in scored if rc < tau_r]

    # Select helpers: prefer normal nodes, use critical only if needed
    selected = []
    remaining_deficit = delta_c

    # First try normal helpers
    for node, hscore, rc, avail in normal:
        if remaining_deficit <= 0:
            break
        selected.append(node)
        remaining_deficit -= avail

    # If still short, use critical helpers
    if remaining_deficit > 0:
        for node, hscore, rc, avail in critical:
            if remaining_deficit <= 0:
                break
            selected.append(node)
            remaining_deficit -= avail

    return selected, all_scores

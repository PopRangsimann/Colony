"""
Recovery-Aware Workload Scheduler
==================================
Assigns workloads to fog nodes considering resource availability,
communication latency, trust, and failure resilience.

Implements Phase IV — Step 3 (Eq. 28–30).

    S^sched  = w₁·Q + w₂·L - w₃·C - w₄·M - w₅·U - w₆·FRI + w₇·ρ  (Eq. 28)
    S̃        = η·S + (1-η)·S_prev                                    (Eq. 29)
    F_k*     = argmin S̃_{j,k}                                        (Eq. 30)
"""

from __future__ import annotations

import sys
import os
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from phase4_load_balancing.fri import compute_fri


def compute_scheduling_score(
    fog_node,
    workload_profile: Dict[str, float],
) -> float:
    """
    Eq. 28:  S^sched = w₁·Q + w₂·L - w₃·C - w₄·M - w₅·U - w₆·FRI + w₇·ρ

    Lower score = better candidate for this workload.

    Parameters
    ----------
    fog_node : FogNode
        Candidate fog node.
    workload_profile : dict
        Workload profile Φ(B_k) from Phase III.
    """
    state = fog_node.runtime_state
    fri = compute_fri(fog_node)

    # Normalize latency to [0, 1]
    lat_min, lat_max = config.LATENCY_RANGE
    lat_norm = (state["L_j"] - lat_min) / max(lat_max - lat_min, 1e-6)
    lat_norm = max(0.0, min(1.0, lat_norm))

    rho_k = workload_profile.get("rho_k", 0.0)

    score = (
        config.SCHED_W1 * state["Q_j"]
        + config.SCHED_W2 * lat_norm
        - config.SCHED_W3 * state["C_j"]
        - config.SCHED_W4 * state["M_j"]
        - config.SCHED_W5 * state["U_j"]
        - config.SCHED_W6 * fri
        + config.SCHED_W7 * rho_k
    )
    return score


def apply_ema_smoothing(
    current_score: float,
    prev_score: Optional[float],
    eta: float = None,
) -> float:
    """
    Eq. 29:  S̃ = η·S + (1-η)·S_prev

    Exponential moving average smoothing for scheduling stability.
    """
    if eta is None:
        eta = config.EMA_ETA
    if prev_score is None:
        return current_score
    return eta * current_score + (1.0 - eta) * prev_score


def assign_workload(
    fog_nodes: list,
    workload_profile: Dict[str, float],
    batch_id: str = "",
) -> Tuple:
    """
    Eq. 30:  F_k* = argmin S̃_{j,k}

    Assign a workload to the fog node with the lowest smoothed
    scheduling score.

    Parameters
    ----------
    fog_nodes : list[FogNode]
        All available fog nodes (excluding MFN/SMFN optionally).
    workload_profile : dict
        Workload profile Φ(B_k).
    batch_id : str
        Batch identifier for tracking.

    Returns
    -------
    (best_node, all_scores)
        The selected fog node and a dict of all smoothed scores.
    """
    candidates = [
        n for n in fog_nodes
        if n.is_alive and not n.is_mfn and not n.is_smfn
    ]

    if not candidates:
        # Fall back to including MFN/SMFN if no workers available
        candidates = [n for n in fog_nodes if n.is_alive]

    if not candidates:
        raise RuntimeError("No alive fog nodes available for scheduling")

    scores = {}
    for node in candidates:
        raw = compute_scheduling_score(node, workload_profile)
        prev = node.prev_sched_scores.get(batch_id)
        smoothed = apply_ema_smoothing(raw, prev)
        node.prev_sched_scores[batch_id] = raw
        scores[node.node_id] = {
            "raw": raw,
            "smoothed": smoothed,
        }

    # Eq. 30:  F_k* = argmin
    best_id = min(scores, key=lambda nid: scores[nid]["smoothed"])
    best_node = next(n for n in candidates if n.node_id == best_id)

    return best_node, scores

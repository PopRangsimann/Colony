"""
Stability-Aware Coordinator Election
======================================
Selects the Master Fog Node (MFN) and Secondary Master Fog Node (SMFN)
based on resource availability, trust, readiness, and stability.

Implements Phase IV — Step 1 (Eq. 24–26).

    R_j         = 1 - (β₁·Q̄ + β₂·M̄ + β₃·L̄)            (Eq. 25)
    S^coord_j   = α₁·C + α₂·M - α₃·L + α₄·U + α₅·R    (Eq. 24)
    Ŝ^coord_j   = S^coord_j - γ·ΔS_j                     (Eq. 26)
"""

from __future__ import annotations

import sys
import os
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config


def compute_readiness(
    queue_norm: float,
    memory_usage_norm: float,
    latency_norm: float,
) -> float:
    """
    Eq. 25:  R_j = 1 - (β₁·Q̄ + β₂·M̄ + β₃·L̄)

    Readiness factor: higher is better (low queue, memory pressure,
    and latency all contribute positively).

    Parameters
    ----------
    queue_norm : float
        Normalized queue occupancy Q̄ ∈ [0, 1].
    memory_usage_norm : float
        Normalized memory usage M̄ ∈ [0, 1]  (1 = fully used).
    latency_norm : float
        Normalized latency L̄ ∈ [0, 1].
    """
    return 1.0 - (
        config.READINESS_BETA_1 * queue_norm
        + config.READINESS_BETA_2 * memory_usage_norm
        + config.READINESS_BETA_3 * latency_norm
    )


def compute_coordination_score(fog_node) -> float:
    """
    Eq. 24:  S^coord_j = α₁·C + α₂·M - α₃·L + α₄·U + α₅·R

    Parameters
    ----------
    fog_node : FogNode
        Fog node with runtime state Ψ(F_j).
    """
    state = fog_node.runtime_state

    # Normalize latency to [0, 1] using configured range
    lat_min, lat_max = config.LATENCY_RANGE
    lat_norm = (state["L_j"] - lat_min) / max(lat_max - lat_min, 1e-6)
    lat_norm = max(0.0, min(1.0, lat_norm))

    # Memory usage is inverse of available memory
    mem_usage_norm = 1.0 - state["M_j"]

    readiness = compute_readiness(
        queue_norm=state["Q_j"],
        memory_usage_norm=mem_usage_norm,
        latency_norm=lat_norm,
    )

    score = (
        config.COORD_ALPHA_1 * state["C_j"]
        + config.COORD_ALPHA_2 * state["M_j"]
        - config.COORD_ALPHA_3 * lat_norm
        + config.COORD_ALPHA_4 * state["U_j"]
        + config.COORD_ALPHA_5 * readiness
    )
    return score


def apply_stability_penalty(
    current_score: float,
    prev_score: Optional[float],
) -> float:
    """
    Eq. 26:  Ŝ^coord_j = S^coord_j - γ·ΔS_j

    Apply a stability penalty to reduce leadership oscillation.

    Parameters
    ----------
    current_score : float
        Current coordination score S^coord_j.
    prev_score : float or None
        Previous epoch's coordination score.
    """
    if prev_score is None:
        return current_score
    delta = abs(current_score - prev_score)
    return current_score - config.STABILITY_GAMMA * delta


def elect_coordinators(
    fog_nodes: list,
) -> Tuple:
    """
    Select the MFN and SMFN from the fog node pool.

    The two nodes with the highest stability-penalized coordination
    scores are selected as MFN and SMFN respectively.

    Parameters
    ----------
    fog_nodes : list[FogNode]
        All fog nodes in the infrastructure.

    Returns
    -------
    (mfn, smfn, scores)
        The elected MFN, SMFN, and a dict of all penalized scores.
    """
    scores = {}
    for node in fog_nodes:
        if not node.is_alive:
            continue
        raw = compute_coordination_score(node)
        penalized = apply_stability_penalty(raw, node.prev_coord_score)
        node.prev_coord_score = raw  # store for next epoch
        scores[node.node_id] = {
            "raw": raw,
            "penalized": penalized,
        }

    # Sort by penalized score descending
    ranked = sorted(
        [(nid, s["penalized"]) for nid, s in scores.items()],
        key=lambda x: x[1],
        reverse=True,
    )

    if len(ranked) < 2:
        raise RuntimeError(
            f"Need at least 2 alive fog nodes for MFN/SMFN election, "
            f"got {len(ranked)}"
        )

    # Clear previous roles
    for node in fog_nodes:
        node.is_mfn = False
        node.is_smfn = False

    # Assign roles
    mfn_id = ranked[0][0]
    smfn_id = ranked[1][0]

    mfn = smfn = None
    for node in fog_nodes:
        if node.node_id == mfn_id:
            node.is_mfn = True
            mfn = node
        elif node.node_id == smfn_id:
            node.is_smfn = True
            smfn = node

    return mfn, smfn, scores

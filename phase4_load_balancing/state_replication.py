"""
Recovery-State Maintenance
===========================
Periodically replicates scheduling-state snapshots to cache nodes
and computes Recovery Scores for autonomous leadership recovery.

Implements Phase IV — Step 4 (Eq. 31–32).

    C_epoch = (Epoch, MFN, SMFN, T)                             (Eq. 31)
    RS_j    = μ₁·Ŝ^coord + μ₂·FRI + μ₃·CF                     (Eq. 32)
"""

from __future__ import annotations

import sys
import os
import time
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from phase4_load_balancing.fri import compute_fri
from phase4_load_balancing.coordinator_election import (
    compute_coordination_score,
    apply_stability_penalty,
)


def build_scheduling_snapshot(
    epoch: int,
    mfn,
    smfn,
    fog_nodes: list,
) -> Dict[str, Any]:
    """
    Eq. 31:  C_epoch = (Epoch, MFN, SMFN, T)

    Construct a scheduling-state snapshot containing the current
    epoch, coordinator identifiers, and the global telemetry table.

    Parameters
    ----------
    epoch : int
        Current scheduling epoch number.
    mfn : FogNode
        The current Master Fog Node.
    smfn : FogNode
        The current Secondary Master Fog Node.
    fog_nodes : list[FogNode]
        All fog nodes (for telemetry collection).
    """
    telemetry_table = {}
    for node in fog_nodes:
        telemetry_table[node.node_id] = node.report_telemetry()

    return {
        "epoch": epoch,
        "mfn_id": mfn.node_id,
        "smfn_id": smfn.node_id,
        "telemetry": telemetry_table,
        "timestamp": time.time(),
    }


def compute_recovery_score(
    fog_node,
    snapshot_timestamp: Optional[float] = None,
) -> float:
    """
    Eq. 32:  RS_j = μ₁·Ŝ^coord + μ₂·FRI + μ₃·CF

    Recovery Score combining coordination fitness, failure resilience,
    and cache freshness.

    Parameters
    ----------
    fog_node : FogNode
        A cache node holding a replicated snapshot.
    snapshot_timestamp : float, optional
        Timestamp of the cached snapshot.  If None, uses the node's
        cache_timestamp attribute.

    Returns
    -------
    float
        Recovery Score RS_j.
    """
    # Coordination score (penalized)
    raw_coord = compute_coordination_score(fog_node)
    penalized_coord = apply_stability_penalty(raw_coord, fog_node.prev_coord_score)

    # FRI
    fri = compute_fri(fog_node)

    # Cache freshness: CF ∈ [0, 1], 1 = perfectly fresh
    ts = snapshot_timestamp or fog_node.cache_timestamp
    if ts is None:
        cf = 0.0
    else:
        age = time.time() - ts
        # Exponential decay: fresh within ~10 seconds
        cf = max(0.0, 1.0 - age / 10.0)

    rs = (
        config.RS_MU_1 * penalized_coord
        + config.RS_MU_2 * fri
        + config.RS_MU_3 * cf
    )
    return rs


def replicate_to_cache_nodes(
    snapshot: Dict[str, Any],
    fog_nodes: list,
    n_cache: int = None,
) -> List:
    """
    Select top-N cache nodes by Recovery Score and replicate the
    scheduling-state snapshot to them.

    Parameters
    ----------
    snapshot : dict
        Scheduling-state snapshot C_epoch.
    fog_nodes : list[FogNode]
        All fog nodes.
    n_cache : int, optional
        Number of cache nodes.  Defaults to config.NUM_CACHE_NODES.

    Returns
    -------
    list[FogNode]
        The selected cache nodes.
    """
    if n_cache is None:
        n_cache = config.NUM_CACHE_NODES

    # Exclude MFN and SMFN from cache candidates
    candidates = [
        n for n in fog_nodes
        if n.is_alive and not n.is_mfn and not n.is_smfn
    ]

    # Compute RS for each candidate
    rs_scores = []
    for node in candidates:
        rs = compute_recovery_score(node)
        rs_scores.append((node, rs))

    # Sort by RS descending and select top-N
    rs_scores.sort(key=lambda x: x[1], reverse=True)
    cache_nodes = []
    for node, rs in rs_scores[:n_cache]:
        node.is_cache_node = True
        node.cached_snapshot = snapshot.copy()
        node.cache_timestamp = time.time()
        cache_nodes.append(node)

    return cache_nodes

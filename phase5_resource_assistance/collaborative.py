"""
Collaborative Assistance and Aggregation
==========================================
Partitions remaining workload across helper nodes proportionally
to their assistance budgets and combines results.

Implements Phase V — Step 3 (Eq. 39–41).

    AB_i = κ·A_i·FRI_i                                     (Eq. 39)
    W_i  = (AB_i / Σ AB_m) · ΔC_k                          (Eq. 40)
    M_k  = Combine(M_1, ..., M_h)                           (Eq. 41)
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from phase4_load_balancing.fri import compute_fri


def compute_assistance_budget(fog_node) -> float:
    """
    Eq. 39:  AB_i = κ · A_i · FRI_i

    Parameters
    ----------
    fog_node : FogNode
        Helper node.

    Returns
    -------
    float
        Assistance budget AB_i.
    """
    available = fog_node.cpu * (1.0 - fog_node.queue_occupancy)
    fri = compute_fri(fog_node)
    return config.KAPPA * available * max(fri, 0.0)


def partition_workload(
    helpers: list,
    delta_c: float,
) -> Dict[str, float]:
    """
    Eq. 40:  W_i = (AB_i / Σ AB_m) · ΔC_k

    Partition the remaining workload proportionally to assistance
    budgets.

    Parameters
    ----------
    helpers : list[FogNode]
        Selected helper nodes.
    delta_c : float
        Total resource deficit to distribute.

    Returns
    -------
    dict[str, float]
        Mapping node_id -> assigned workload fraction W_i.
    """
    budgets = {}
    for node in helpers:
        budgets[node.node_id] = compute_assistance_budget(node)

    total_budget = sum(budgets.values())
    if total_budget <= 0:
        # Equal split as fallback
        n = len(helpers)
        return {node.node_id: delta_c / n for node in helpers}

    partitions = {}
    for node in helpers:
        ab = budgets[node.node_id]
        partitions[node.node_id] = (ab / total_budget) * delta_c

    return partitions


def combine_results(
    partial_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Eq. 41:  M_k = Combine(M_1, ..., M_h)

    Combine partial results from helper nodes into a final result.

    Parameters
    ----------
    partial_results : list[dict]
        Results from each helper node, each containing 'result' bytes
        and execution metadata.

    Returns
    -------
    dict
        Combined result with all fragments concatenated and metadata.
    """
    if not partial_results:
        return {"result": b"", "fragments": 0, "total_exec_time": 0.0}

    # Concatenate all result fragments
    combined_data = b"".join(
        r.get("result", b"") for r in partial_results
        if isinstance(r.get("result"), bytes)
    )

    total_time = sum(
        r.get("exec_time", 0.0) for r in partial_results
    )

    return {
        "result": combined_data,
        "fragments": len(partial_results),
        "total_exec_time": total_time,
        "node_ids": [r.get("node_id", "?") for r in partial_results],
    }

"""
Failure Resilience Index (FRI)
===============================
Quantifies the long-term operational reliability of each fog node
by combining trust, readiness, and historical failure rate.

Implements Phase IV — Step 2 (Eq. 27).

    FRI_j = θ₁·U_j + θ₂·R_j - θ₃·FR_j
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from phase4_load_balancing.coordinator_election import compute_readiness


def compute_fri(fog_node) -> float:
    """
    Eq. 27:  FRI_j = θ₁·U + θ₂·R - θ₃·FR

    Parameters
    ----------
    fog_node : FogNode
        Fog node with runtime state and failure history.

    Returns
    -------
    float
        Failure Resilience Index.  Higher = more resilient.
    """
    state = fog_node.runtime_state

    # Normalize latency
    lat_min, lat_max = config.LATENCY_RANGE
    lat_norm = (state["L_j"] - lat_min) / max(lat_max - lat_min, 1e-6)
    lat_norm = max(0.0, min(1.0, lat_norm))

    mem_usage_norm = 1.0 - state["M_j"]

    readiness = compute_readiness(
        queue_norm=state["Q_j"],
        memory_usage_norm=mem_usage_norm,
        latency_norm=lat_norm,
    )

    fri = (
        config.FRI_THETA_1 * state["U_j"]
        + config.FRI_THETA_2 * readiness
        - config.FRI_THETA_3 * fog_node.failure_rate
    )
    return fri

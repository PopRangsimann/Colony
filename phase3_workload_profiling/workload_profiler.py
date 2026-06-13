"""
Scheduling-Aware Workload Profiling
====================================
Derives workload descriptors for adaptive scheduling and recovery.

Implements Phase III — Step 3 (Eq. 20–22).

    Φ(B_k) = (S_k, ω_k, δ_k, ρ_k)                       (Eq. 20)
    ω_k    = α₁·S_k + α₂·V_k + α₃·D_k                  (Eq. 21)
    ρ_k    = β₁·δ_k + β₂·ω_k + β₃·P_k                  (Eq. 22)
"""

from __future__ import annotations

import random
import sys
import os
from typing import Any, Dict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config


def compute_workload_intensity(
    batch_size: int,
    payload_volume: float,
    processing_complexity: float,
) -> float:
    """
    Eq. 21:  ω_k = α₁·S_k + α₂·V_k + α₃·D_k

    Parameters
    ----------
    batch_size : int
        Number of packets in the batch (S_k).
    payload_volume : float
        Aggregated payload volume in KB (V_k).
    processing_complexity : float
        Expected processing complexity normalized to [0, 1] (D_k).
    """
    return (
        config.INTENSITY_ALPHA_1 * batch_size
        + config.INTENSITY_ALPHA_2 * payload_volume
        + config.INTENSITY_ALPHA_3 * processing_complexity
    )


def compute_deadline_urgency(
    deadline: float,
    current_time: float,
) -> float:
    """
    Compute deadline urgency δ_k.

    Higher values indicate more urgent deadlines.
    Returns a value in [0, ∞) where 0 means plenty of time.
    """
    remaining = max(deadline - current_time, 0.001)
    return 1.0 / remaining


def compute_recovery_priority(
    deadline_urgency: float,
    workload_intensity: float,
    app_priority: float,
) -> float:
    """
    Eq. 22:  ρ_k = β₁·δ_k + β₂·ω_k + β₃·P_k

    Parameters
    ----------
    deadline_urgency : float
        δ_k — inverse of remaining time to deadline.
    workload_intensity : float
        ω_k — composite intensity score.
    app_priority : float
        P_k — application-defined priority (higher = more important).
    """
    return (
        config.PRIORITY_BETA_1 * deadline_urgency
        + config.PRIORITY_BETA_2 * workload_intensity
        + config.PRIORITY_BETA_3 * app_priority
    )


def profile_workload(
    batch: Dict[str, Any],
    deadline: float = None,
    app_priority: float = 1.0,
) -> Dict[str, float]:
    """
    Eq. 20:  Φ(B_k) = (S_k, ω_k, δ_k, ρ_k)

    Derive the full scheduling-aware workload profile.

    Parameters
    ----------
    batch : dict
        Micro-batch from form_micro_batch().
    deadline : float, optional
        Absolute deadline timestamp.  If None, randomly assigned
        from config.WORKLOAD_DEADLINE_RANGE relative to batch time.
    app_priority : float
        Application-defined workload priority P_k.

    Returns
    -------
    dict
        Workload profile Φ(B_k) with keys: S_k, V_k, D_k,
        omega_k, delta_k, rho_k, deadline.
    """
    import time as _time

    s_k = batch["size"]

    # Aggregate payload volume (sum of ciphertext sizes in KB)
    v_k = sum(len(pkt["ct"]) for pkt in batch["packets"]) / 1024.0

    # Estimated processing complexity (normalized)
    d_k = min(1.0, s_k / 50.0)  # saturates at 50 packets

    # Eq. 21
    omega_k = compute_workload_intensity(s_k, v_k, d_k)

    # Deadline
    now = _time.time()
    if deadline is None:
        deadline = now + random.uniform(*config.WORKLOAD_DEADLINE_RANGE)

    # Deadline urgency
    delta_k = compute_deadline_urgency(deadline, now)

    # Eq. 22
    rho_k = compute_recovery_priority(delta_k, omega_k, app_priority)

    return {
        "S_k": s_k,
        "V_k": v_k,
        "D_k": d_k,
        "omega_k": omega_k,
        "delta_k": delta_k,
        "rho_k": rho_k,
        "deadline": deadline,
        "app_priority": app_priority,
    }

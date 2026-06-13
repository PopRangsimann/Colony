"""
Assistance Request Generation
===============================
Detects overloaded or deadline-threatened workloads and generates
assistance requests for collaborative processing.

Implements Phase V — Step 1 (Eq. 33–35).

    Trigger:  T_k^est > T_k^deadline                        (Eq. 33)
    ΔC_k    = max(0, C_k^req - C_k^avail)                  (Eq. 34)
    AR_k    = (B_k, ΔC_k, δ_k, ρ_k)                        (Eq. 35)
"""

from __future__ import annotations

import sys
import os
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def check_assistance_needed(
    t_est: float,
    t_deadline: float,
    delta_k: float = 0.0,
    rho_k: float = 0.0,
    urgency_threshold: float = 2.0,
) -> bool:
    """
    Eq. 33:  T_k^est > T_k^deadline

    Determine if assistance is needed for a workload.
    Also triggers on high urgency or recovery priority.

    Parameters
    ----------
    t_est : float
        Estimated completion time (absolute timestamp).
    t_deadline : float
        Workload deadline (absolute timestamp).
    delta_k : float
        Deadline urgency score.
    rho_k : float
        Recovery priority score.
    urgency_threshold : float
        Threshold above which δ_k or ρ_k triggers assistance.
    """
    if t_est > t_deadline:
        return True
    if delta_k > urgency_threshold or rho_k > urgency_threshold:
        return True
    return False


def compute_resource_deficit(
    c_required: float,
    c_available: float,
) -> float:
    """
    Eq. 34:  ΔC_k = max(0, C_k^req - C_k^avail)

    Estimate the computational deficit.

    Parameters
    ----------
    c_required : float
        Required computational resources for the workload.
    c_available : float
        Currently available resources on the hosting node.
    """
    return max(0.0, c_required - c_available)


def generate_request(
    batch: Dict[str, Any],
    delta_c: float,
    delta_k: float,
    rho_k: float,
) -> Dict[str, Any]:
    """
    Eq. 35:  AR_k = (B_k, ΔC_k, δ_k, ρ_k)

    Generate a formal assistance request.

    Parameters
    ----------
    batch : dict
        Workload batch B_k.
    delta_c : float
        Resource deficit ΔC_k.
    delta_k : float
        Deadline urgency score.
    rho_k : float
        Recovery priority score.

    Returns
    -------
    dict
        Assistance request AR_k.
    """
    return {
        "BID": batch.get("BID", "unknown"),
        "batch": batch,
        "delta_c": delta_c,
        "delta_k": delta_k,
        "rho_k": rho_k,
    }

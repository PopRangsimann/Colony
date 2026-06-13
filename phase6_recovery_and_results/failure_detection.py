"""
Coordinator Failure Detection
===============================
Monitors MFN and SMFN liveness through periodic heartbeat messages.

Implements Phase VI — Step 1 (Eq. 42).

    Coordinator failed if:  t_now - t_last > τ_H
"""

from __future__ import annotations

import sys
import os
import time
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config


class HeartbeatMonitor:
    """
    Monitors liveness of MFN and SMFN through heartbeat tracking.

    Parameters
    ----------
    tau_h : float, optional
        Failure detection threshold in seconds.
        Defaults to config.TAU_H.
    """

    def __init__(self, tau_h: float = None):
        self.tau_h = tau_h if tau_h is not None else config.TAU_H

    def check_liveness(
        self,
        t_last: float,
        t_now: float = None,
    ) -> bool:
        """
        Eq. 42:  failed if t_now - t_last > τ_H

        Parameters
        ----------
        t_last : float
            Timestamp of the most recent heartbeat.
        t_now : float, optional
            Current time.  Defaults to time.time().

        Returns
        -------
        bool
            True if the node is alive (heartbeat within threshold).
        """
        if t_now is None:
            t_now = time.time()
        return (t_now - t_last) <= self.tau_h

    def detect_failures(
        self,
        mfn,
        smfn,
        t_now: float = None,
    ) -> Dict[str, bool]:
        """
        Check liveness of both MFN and SMFN.

        Returns
        -------
        dict
            {'mfn_alive': bool, 'smfn_alive': bool}
        """
        if t_now is None:
            t_now = time.time()

        return {
            "mfn_alive": self.check_liveness(mfn.last_heartbeat, t_now),
            "smfn_alive": self.check_liveness(smfn.last_heartbeat, t_now),
            "mfn_id": mfn.node_id,
            "smfn_id": smfn.node_id,
        }

"""
Ref[3] — Ala'anzy et al.: OLB Algorithm
==========================================
Optimised Load Balancing from:
"Dynamic Load Balancing for Enhanced Network Performance"
(IEEE Access, 2024)

Scheduling: assigns each workload to the fog node with the lowest
total latency = communication_latency + computing_latency.
  - Comm latency (Eq. 6):  Lm = TL / (1 - TL)
  - Comp latency (Eq. 9):  Lp = CL / (1 - CL)
  - Assignment (Eq. 10):   argmin(L_total_j + d_i)

No coordinator hierarchy, no fault tolerance, no helpers.
"""

from __future__ import annotations

import sys
import os
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evaluation import sim_config
from evaluation.schemes.base import BaseScheme
from evaluation.environment import SimFogNode, Workload


class Ref3Scheme(BaseScheme):
    """Ala'anzy et al. OLB: latency-based greedy assignment."""

    def _comm_latency(self, node: SimFogNode) -> float:
        """
        OLB Eq. 6: Lm = TL / (1 - TL)
        Traffic load TL approximated from queue occupancy.
        """
        tl = min(node.queue_occupancy, 0.99)  # avoid division by zero
        return (tl / (1.0 - tl)) * node.comm_latency_ms()

    def _comp_latency(self, node: SimFogNode, workload_size: float) -> float:
        """
        OLB Eq. 9: Lp = CL / (1 - CL)
        Computing load CL approximated from CPU utilization.
        """
        cl = min(node.queue_occupancy * sim_config.REF3_CL_QUEUE_WEIGHT + (1.0 - node.cpu) * sim_config.REF3_CL_CPU_WEIGHT, 0.99)
        base_proc = node.processing_time(workload_size) * 1000
        return (cl / (1.0 - cl)) * max(base_proc, 0.1)

    def _total_latency(self, node: SimFogNode, workload: Workload) -> float:
        """OLB Eq. 10: L_total = Lm + Lp"""
        return self._comm_latency(node) + self._comp_latency(node, workload.size)

    # ─── Interface ──────────────────────────────────────────────────

    def elect_coordinator(
        self, nodes: List[SimFogNode]
    ) -> Tuple[Optional[SimFogNode], Optional[SimFogNode]]:
        # OLB has no coordinator concept; pick first two alive as placeholders
        alive = [n for n in nodes if n.is_alive]
        mfn = alive[0] if len(alive) >= 1 else None
        smfn = alive[1] if len(alive) >= 2 else None
        return mfn, smfn

    def schedule_workload(
        self, nodes, workload, mfn=None, smfn=None
    ) -> Optional[SimFogNode]:
        # Eq. 10: argmin(L_total_j + d_i)
        candidates = [n for n in nodes if n.is_alive]
        if not candidates:
            return None

        best, best_lat = None, float("inf")
        for n in candidates:
            lat = self._total_latency(n, workload)
            if lat < best_lat:
                best_lat = lat
                best = n
        return best

    def handle_failure(self, nodes, failed_node) -> float:
        # No built-in recovery; full re-election by polling all nodes
        alive_count = sum(1 for n in nodes if n.is_alive)
        return sim_config.REF3_REELECTION_PER_NODE_MS * alive_count

    def request_assistance(self, nodes, overloaded, workload) -> List[SimFogNode]:
        # OLB has no collaborative assistance mechanism
        return []

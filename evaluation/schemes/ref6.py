"""
Ref[6] — Jasim & Al-Raweshidy: SDN-GH Algorithm
==================================================
SDN-based Greedy Heuristic from:
"Adaptive SDN-Based Load Balancing Method for Edge/Fog-Based
Real-Time Healthcare Systems" (IEEE Systems Journal, 2024)

Scheduling: centralized SDN controller with global view.
  - Offload only if t_offloading < t_local (Eq. 8)
  - Queue model: tMC = fQ(K·λ) + K·λ/μ (M/M/1-style, Eq. 4)
  - 7 cascading scenarios: try local → neighbors → higher tier

Recovery: SDN controller state reconstruction (proportional to nodes).
Helper: basic load migration to least-loaded neighbor.
"""

from __future__ import annotations

import sys
import os
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evaluation import sim_config
from evaluation.schemes.base import BaseScheme
from evaluation.environment import SimFogNode, Workload


class Ref6Scheme(BaseScheme):
    """Jasim & Al-Raweshidy: SDN-assisted greedy heuristic."""

    def _queue_latency(self, node: SimFogNode) -> float:
        """
        M/M/1 queue model (Eq. 4): tMC = fQ(K·λ_sum) + K·λ_sum/μ
        Simplified: queue_wait ∝ occupancy / (1 - occupancy)
        """
        rho = min(node.queue_occupancy, 0.99)
        if rho < 0.01:
            return 0.0
        return (rho / (1.0 - rho)) * sim_config.REF6_QUEUE_SCALE_MS

    def _local_exec_time(self, node: SimFogNode, workload: Workload) -> float:
        """Estimated local execution time including queue wait."""
        proc = node.processing_time(workload.size) * 1000
        queue = self._queue_latency(node)
        comm = node.comm_latency_ms()
        return proc + queue + comm

    def _remote_exec_time(
        self, remote: SimFogNode, workload: Workload
    ) -> float:
        """Estimated remote execution time (offloading overhead)."""
        proc = remote.processing_time(workload.size) * 1000
        queue = self._queue_latency(remote)
        # Extra communication for offloading (round trip)
        comm = remote.comm_latency_ms() * 2.0
        return proc + queue + comm

    # ─── Interface ──────────────────────────────────────────────────

    def elect_coordinator(
        self, nodes: List[SimFogNode]
    ) -> Tuple[Optional[SimFogNode], Optional[SimFogNode]]:
        # SDN controller = centralized node with most capacity
        alive = sorted(
            [n for n in nodes if n.is_alive],
            key=lambda n: n.cpu * n.memory,
            reverse=True,
        )
        mfn = alive[0] if len(alive) >= 1 else None
        smfn = alive[1] if len(alive) >= 2 else None
        return mfn, smfn

    def schedule_workload(
        self, nodes, workload, mfn=None, smfn=None
    ) -> Optional[SimFogNode]:
        candidates = [n for n in nodes if n.is_alive]
        if not candidates:
            return None

        # Find local candidate (least queue wait)
        local = min(candidates, key=lambda n: self._queue_latency(n))
        t_local = self._local_exec_time(local, workload)

        # SDN-GH: try offloading to better node if beneficial (Eq. 8)
        best_node = local
        best_time = t_local

        for n in candidates:
            if n.node_id == local.node_id:
                continue
            t_remote = self._remote_exec_time(n, workload)
            # Eq. 8: offload only if t_offloading < t_local
            if t_remote < best_time:
                best_time = t_remote
                best_node = n

        return best_node

    def handle_failure(self, nodes, failed_node) -> float:
        # SDN state reconstruction: base + per-node collection
        alive_count = sum(1 for n in nodes if n.is_alive)
        return (
            sim_config.REF6_STATE_RECON_BASE_MS
            + sim_config.REF6_STATE_RECON_PER_NODE_MS * alive_count
        )

    def request_assistance(self, nodes, overloaded, workload) -> List[SimFogNode]:
        # Basic load migration: offload to least-loaded neighbor
        candidates = [
            n for n in nodes
            if n.is_alive and n.node_id != overloaded.node_id
        ]
        if not candidates:
            return []

        # Pick the single least-loaded node (no recovery awareness)
        best = min(candidates, key=lambda n: n.queue_occupancy)
        if best.queue_occupancy < sim_config.REF6_OFFLOAD_THRESHOLD:
            return [best]
        return []

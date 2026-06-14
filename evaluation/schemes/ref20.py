"""
Ref[20] — Kashyap et al.: MHHO-ACO Hybrid
=============================================
Modified Harris-Hawks Optimization + Ant Colony Optimization from:
"A hybrid approach for fault-tolerance aware load balancing in
fog computing" (Cluster Computing, 2024)

Scheduling: fitness-based scoring (Eq. 5):
    fitness(i) = 1 / (1 + f(i))
    f(i) = w_makespan * makespan + w_energy * energy + w_reliability * (1 - rel)

Recovery: ACO pheromone-trail reconvergence (multi-step iterative).
Fault tolerance: pheromone-guided rerouting to available nodes.
"""

from __future__ import annotations

import sys
import os
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evaluation import sim_config
from evaluation.schemes.base import BaseScheme
from evaluation.environment import SimFogNode, Workload


class Ref20Scheme(BaseScheme):
    """Kashyap et al.: MHHO-ACO hybrid meta-heuristic."""

    def _makespan(self, node: SimFogNode, workload: Workload) -> float:
        """Estimated makespan (Eq. 8): queue_depth * avg_processing_time."""
        avg_proc = node.processing_time(0.5) * 1000  # ms
        return node.queue_load * avg_proc + node.processing_time(workload.size) * 1000

    def _energy(self, node: SimFogNode, workload: Workload) -> float:
        """Estimated energy ∝ CPU utilization * processing time."""
        proc = node.processing_time(workload.size) * 1000
        return node.cpu * proc  # higher CPU = more energy

    def _reliability(self, node: SimFogNode) -> float:
        """Reliability = 1 - failure_rate."""
        return 1.0 - node.failure_rate

    def _fitness(self, node: SimFogNode, workload: Workload) -> float:
        """
        MHHO Eq. 5: fitness(i) = 1 / (1 + f(i))
        f(i) = weighted sum of makespan, energy, and unreliability.
        Higher fitness = better node.
        """
        ms = self._makespan(node, workload)
        en = self._energy(node, workload)
        rel = self._reliability(node)

        # Normalize makespan and energy to [0, 1] range approximately
        ms_norm = min(ms / 1000.0, 1.0)
        en_norm = min(en / sim_config.REF20_ENERGY_NORM, 1.0)

        f = (
            sim_config.REF20_W_MAKESPAN * ms_norm
            + sim_config.REF20_W_ENERGY * en_norm
            + sim_config.REF20_W_RELIABILITY * (1.0 - rel)
        )
        return 1.0 / (1.0 + f)

    # ─── Interface ──────────────────────────────────────────────────

    def elect_coordinator(
        self, nodes: List[SimFogNode]
    ) -> Tuple[Optional[SimFogNode], Optional[SimFogNode]]:
        # MHHO-ACO has no explicit coordinator; pick by reliability + capacity
        alive = [n for n in nodes if n.is_alive]
        alive.sort(
            key=lambda n: n.cpu * self._reliability(n),
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

        # Select node with highest fitness (Eq. 5)
        best = max(candidates, key=lambda n: self._fitness(n, workload))
        return best

    def handle_failure(self, nodes, failed_node, in_flight_tasks=0) -> float:
        # ACO reconvergence: iterations scale with system complexity
        import random, math
        iterations = (
            sim_config.REF20_RECONVERGE_BASE_ITERATIONS
            + sim_config.REF20_RECONVERGE_TASK_SCALE * math.sqrt(max(in_flight_tasks, 1))
        )
        base = iterations * sim_config.REF20_ITERATION_MS
        jitter = random.uniform(
            -sim_config.REF20_RECOVERY_JITTER_MS,
            sim_config.REF20_RECOVERY_JITTER_MS,
        )
        return max(1.0, base + jitter)

    def request_assistance(self, nodes, overloaded, workload) -> List[SimFogNode]:
        # ACO-based rerouting: select most reliable alternative node
        candidates = [
            n for n in nodes
            if n.is_alive and n.node_id != overloaded.node_id
        ]
        if not candidates:
            return []

        # Pick by reliability (ACO pheromone ≈ historical success)
        best = max(candidates, key=lambda n: self._reliability(n))
        if self._reliability(best) > 0.5:
            return [best]
        return []

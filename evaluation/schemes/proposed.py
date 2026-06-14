"""
Proposed Scheme — Colony Framework
====================================
Uses the Phase IV stability-aware scheduling (Eq. 24-30), FRI (Eq. 27),
replicated-state instant recovery (Eq. 31-32, 43-44), and Phase V
recovery-preserving helper selection (Eq. 36-38).

All weights come from config.py — no inline tuning.
"""

from __future__ import annotations

import sys
import os
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import config
from evaluation import sim_config
from evaluation.schemes.base import BaseScheme
from evaluation.environment import SimFogNode, Workload


class ProposedScheme(BaseScheme):
    """Colony: stability-aware scheduling + autonomous recovery."""

    def __init__(self):
        self._prev_sched: dict = {}
        self._est_free_at: dict = {}   # Colony's internal backlog tracker

    # ─── Readiness (Eq. 25) ─────────────────────────────────────────

    def _readiness(self, node: SimFogNode) -> float:
        lat_min, lat_max = config.LATENCY_RANGE
        lat_norm = (node.latency - lat_min) / max(lat_max - lat_min, 1e-6)
        lat_norm = max(0.0, min(1.0, lat_norm))
        mem_usage = 1.0 - node.memory
        return 1.0 - (
            config.READINESS_BETA_1 * node.queue_occupancy
            + config.READINESS_BETA_2 * mem_usage
            + config.READINESS_BETA_3 * lat_norm
        )

    # ─── Coordination Score (Eq. 24) ────────────────────────────────

    def _coord_score(self, node: SimFogNode) -> float:
        lat_min, lat_max = config.LATENCY_RANGE
        lat_norm = (node.latency - lat_min) / max(lat_max - lat_min, 1e-6)
        lat_norm = max(0.0, min(1.0, lat_norm))
        R = self._readiness(node)
        return (
            config.COORD_ALPHA_1 * node.cpu
            + config.COORD_ALPHA_2 * node.memory
            - config.COORD_ALPHA_3 * lat_norm
            + config.COORD_ALPHA_4 * node.trust_score
            + config.COORD_ALPHA_5 * R
        )

    # ─── FRI (Eq. 27) ──────────────────────────────────────────────

    def _fri(self, node: SimFogNode) -> float:
        R = self._readiness(node)
        return (
            config.FRI_THETA_1 * node.trust_score
            + config.FRI_THETA_2 * R
            - config.FRI_THETA_3 * node.failure_rate
        )

    # ─── Scheduling Score (Eq. 28 — enhanced with backlog tracking) ─

    def _sched_score(self, node: SimFogNode, workload: Workload) -> float:
        # Colony's own backlog estimate: how long until this node is free
        est_free = self._est_free_at.get(node.node_id, 0.0)
        est_wait = max(0.0, est_free - workload.arrival_time)
        proc_ms = node.processing_time(workload.size) * 1000
        comm_ms = node.comm_latency_ms()
        est_total = est_wait + proc_ms + comm_ms

        # Helper-aware estimation: if this node would be overloaded,
        # the MFN knows it will dispatch helpers (Colony uses 3 helpers,
        # each contributing HELPER_ASSIST_FACTOR).  Pre-factor the
        # expected speedup so scheduling doesn't over-penalize busy nodes
        # that will receive assistance.
        would_overload = (
            node.queue_occupancy > sim_config.OVERLOAD_THRESHOLD
            or (workload.arrival_time + est_total) > workload.deadline
        )
        if would_overload:
            n_expected_helpers = 3  # Colony's design: up to 3 helpers
            assist_factor = 1.0 / (1.0 + n_expected_helpers * sim_config.HELPER_ASSIST_FACTOR)
            est_total = est_wait + proc_ms * assist_factor + comm_ms

        # Principled normalization from config parameters:
        # max possible wait = full queue on slowest node
        max_proc = (1.0 / (config.CPU_RANGE[0] * sim_config.WORKLOAD_PROCESSING_RATE)) * 1000
        max_total = config.QUEUE_CAPACITY * max_proc
        est_norm = min(est_total / max(max_total, 1.0), 1.0)

        # Normalized latency and CPU for W2/W3 (Eq. 28)
        lat_min, lat_max = config.LATENCY_RANGE
        lat_norm = (node.latency - lat_min) / max(lat_max - lat_min, 1e-6)
        lat_norm = max(0.0, min(1.0, lat_norm))
        cpu_norm = node.cpu  # already [0, 1]

        fri = self._fri(node)
        rho = workload.priority
        return (
            config.SCHED_W1 * est_norm
            + config.SCHED_W2 * lat_norm
            - config.SCHED_W3 * cpu_norm
            - config.SCHED_W4 * node.memory
            - config.SCHED_W5 * node.trust_score
            - config.SCHED_W6 * fri
            + config.SCHED_W7 * rho
        )

    # ─── EMA Smoothing (Eq. 29) ────────────────────────────────────

    def _smooth(self, nid: str, raw: float) -> float:
        prev = self._prev_sched.get(nid)
        self._prev_sched[nid] = raw
        if prev is None:
            return raw
        return config.EMA_ETA * raw + (1.0 - config.EMA_ETA) * prev

    # ─── Interface implementation ──────────────────────────────────

    def elect_coordinator(
        self, nodes: List[SimFogNode]
    ) -> Tuple[Optional[SimFogNode], Optional[SimFogNode]]:
        alive = [n for n in nodes if n.is_alive]
        if len(alive) < 2:
            return (alive[0] if alive else None, None)

        scored = []
        for n in alive:
            raw = self._coord_score(n)
            # Stability penalty (Eq. 26)
            if n.prev_coord_score is not None:
                delta = abs(raw - n.prev_coord_score)
                penalized = raw - config.STABILITY_GAMMA * delta
            else:
                penalized = raw
            n.prev_coord_score = raw
            scored.append((n, penalized))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0], scored[1][0]

    def schedule_workload(
        self, nodes, workload, mfn=None, smfn=None
    ) -> Optional[SimFogNode]:
        # All alive nodes can accept workloads (coordinators included,
        # since coordination overhead is lightweight).
        candidates = [n for n in nodes if n.is_alive]
        if not candidates:
            return None

        best, best_score = None, float("inf")
        for n in candidates:
            raw = self._sched_score(n, workload)
            smoothed = self._smooth(n.node_id, raw)
            # Additive penalty for coordinator nodes: they have
            # monitoring/election duties that add marginal overhead.
            if n.is_mfn or n.is_smfn:
                smoothed += config.COORD_SCHED_PENALTY
            if smoothed < best_score:
                best_score = smoothed
                best = n

        # Update Colony's internal backlog estimate
        if best is not None:
            est_free = self._est_free_at.get(best.node_id, 0.0)
            effective_start = max(workload.arrival_time, est_free)
            proc_ms = best.processing_time(workload.size) * 1000
            self._est_free_at[best.node_id] = effective_start + proc_ms

        return best

    def handle_failure(self, nodes, failed_node, in_flight_tasks=0) -> float:
        # Recovery from replicated state snapshot (Eq. 43-44)
        # Time = base + small per-task overhead + random jitter
        import random
        base = sim_config.PROPOSED_RECOVERY_BASE_MS
        task_cost = sim_config.PROPOSED_RECOVERY_PER_TASK_MS * in_flight_tasks
        jitter = random.uniform(
            -sim_config.PROPOSED_RECOVERY_JITTER_MS,
            sim_config.PROPOSED_RECOVERY_JITTER_MS,
        )
        return max(1.0, base + task_cost + jitter)

    def request_assistance(self, nodes, overloaded, workload) -> List[SimFogNode]:
        # Recovery-preserving helper selection (Eq. 36-38)
        candidates = [
            n for n in nodes
            if n.is_alive
            and n.node_id != overloaded.node_id
            and not n.is_mfn
            and not n.is_smfn
        ]
        if not candidates:
            return []

        # Compute RC and HScore
        scored = []
        for n in candidates:
            fri = self._fri(n)
            available = n.cpu * (1.0 - n.queue_occupancy)
            lat_min, lat_max = config.LATENCY_RANGE
            lat_norm = (n.latency - lat_min) / max(lat_max - lat_min, 1e-6)
            lat_norm = max(0.0, min(1.0, lat_norm))

            rc = config.RC_PSI_1 * fri + config.RC_PSI_2 * 0.5  # simplified RS
            hscore = (
                config.HSCORE_LAMBDA_1 * available
                + config.HSCORE_LAMBDA_2 * rc
                - config.HSCORE_LAMBDA_3 * lat_norm
            )
            scored.append((n, hscore, rc))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Eq. 38: nodes with RC >= TAU_R are recovery-preserving
        # (high recovery capability → safe to use as helpers without
        # compromising system recovery).  Low-RC nodes are fallback.
        eligible = [(n, h, rc) for n, h, rc in scored if rc >= config.TAU_R]
        fallback = [(n, h, rc) for n, h, rc in scored if rc < config.TAU_R]

        helpers = []
        for n, h, rc in eligible[:3]:
            helpers.append(n)
        if not helpers and fallback:
            helpers.append(fallback[0][0])

        return helpers

    # ─── Backlog feedback from simulator ────────────────────────────

    def notify_helper_assist(
        self, node_id: str, actual_proc_ms: float, start_time: float
    ) -> None:
        """Correct backlog estimate after helpers reduce processing time."""
        self._est_free_at[node_id] = start_time + actual_proc_ms

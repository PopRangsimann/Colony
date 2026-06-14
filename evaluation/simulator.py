"""
Discrete-Event Simulator
==========================
Processes workload arrivals, scheduling decisions, queue execution,
and failure injections.  Records timestamped events for metric
computation.  Each scheme plugs in via the BaseScheme interface.

All timing is simulated (not wall-clock) for deterministic results.
"""

from __future__ import annotations

import sys
import os
from typing import Any, Dict, List, Type

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluation import sim_config

from evaluation.environment import Environment, SimFogNode, Workload, FailureEvent
from evaluation.schemes.base import BaseScheme


class Simulator:
    """
    Discrete-event simulator that runs a scheme against an environment.

    Parameters
    ----------
    env : Environment
        Cloned environment (scheme gets its own copy).
    scheme : BaseScheme
        Scheduling scheme instance.
    """

    def __init__(self, env: Environment, scheme: BaseScheme):
        self.env = env
        self.scheme = scheme
        self.events: List[Dict[str, Any]] = []
        self.sim_time: float = 0.0
        self._recovery_until: float = 0.0  # time when recovery completes

        # Per-node: track when each node finishes its current work
        self._node_free_at: Dict[str, float] = {}
        for n in self.env.fog_nodes:
            self._node_free_at[n.node_id] = 0.0

        # Elect initial coordinators
        self.mfn, self.smfn = self.scheme.elect_coordinator(self.env.fog_nodes)
        if self.mfn:
            self.mfn.is_mfn = True
        if self.smfn:
            self.smfn.is_smfn = True

        # Build failure schedule
        self._failure_idx = 0
        self._sorted_failures = sorted(
            self.env.failure_events, key=lambda f: f.time
        )

    def run(self) -> List[Dict[str, Any]]:
        """
        Run the full simulation and return event logs.

        Returns
        -------
        list[dict]
            Event logs for metric computation.
        """
        for workload in self.env.workloads:
            self.sim_time = workload.arrival_time

            # ─── Check for failure injections before this workload ──
            self._process_failures_up_to(self.sim_time)

            # ─── If system is recovering, workloads are dropped ────────
            if self.sim_time < self._recovery_until:
                self.events.append({
                    "wid": workload.wid,
                    "arrival_time": workload.arrival_time,
                    "deadline": workload.deadline,
                    "completed": False,
                    "reason": "system_recovering",
                })
                continue

            # ─── Schedule this workload ─────────────────────────────
            alive_nodes = [n for n in self.env.fog_nodes if n.is_alive]
            if not alive_nodes:
                self.events.append({
                    "wid": workload.wid,
                    "arrival_time": workload.arrival_time,
                    "deadline": workload.deadline,
                    "completed": False,
                    "reason": "no_alive_nodes",
                })
                continue

            target = self.scheme.schedule_workload(
                alive_nodes, workload, self.mfn, self.smfn
            )

            if target is None:
                self.events.append({
                    "wid": workload.wid,
                    "arrival_time": workload.arrival_time,
                    "deadline": workload.deadline,
                    "completed": False,
                    "reason": "scheduling_failed",
                })
                continue

            # ─── Simulate execution with proper queuing ─────────────
            processing_ms = target.processing_time(workload.size) * 1000
            comm_ms = target.comm_latency_ms()

            # Queue wait: node is busy until _node_free_at
            node_free = self._node_free_at.get(target.node_id, 0.0)
            effective_arrival = max(self.sim_time, node_free)
            queue_wait_ms = effective_arrival - self.sim_time

            total_latency = comm_ms + queue_wait_ms + processing_ms
            completion_time = workload.arrival_time + total_latency

            # Update node state
            target.queue_load = min(
                target.queue_load + 1, target.queue_capacity
            )
            target.total_tasks += 1

            # Check if overloaded → request assistance
            overloaded = (
                target.queue_occupancy > sim_config.OVERLOAD_THRESHOLD
                or completion_time > workload.deadline
            )
            if overloaded:
                helpers = self.scheme.request_assistance(
                    self.env.fog_nodes, target, workload
                )
                if helpers:
                    # Distribute load across helpers: reduce processing
                    n_helpers = len(helpers)
                    assist_factor = 1.0 / (1.0 + n_helpers * sim_config.HELPER_ASSIST_FACTOR)
                    processing_ms *= assist_factor
                    total_latency = (
                        comm_ms + queue_wait_ms + processing_ms
                    )
                    completion_time = workload.arrival_time + total_latency

                    # Helpers contribute processing power; workload
                    # remains in primary node's queue (no queue impact).
                    for h in helpers:
                        h.total_tasks += 1

            # Update node busy time (uses final processing_ms,
            # which may have been reduced by helper assistance).
            self._node_free_at[target.node_id] = (
                effective_arrival + processing_ms
            )

            # Drain queue slowly (only drain if enough time passed)
            if target.queue_load > 1:
                drain = max(1, int(queue_wait_ms / max(processing_ms, 1)))
                target.queue_load = max(0, target.queue_load - drain)

            # Update trust based on success
            success = completion_time <= workload.deadline
            if success:
                target.trust_score = min(
                    1.0, target.trust_score + sim_config.TRUST_INCREMENT
                )
            else:
                target.trust_score = max(
                    0.0, target.trust_score - sim_config.TRUST_DECREMENT
                )
                target.failure_count += 1

            self.events.append({
                "wid": workload.wid,
                "arrival_time": workload.arrival_time,
                "completion_time": completion_time,
                "deadline": workload.deadline,
                "completed": True,
                "on_time": success,
                "node_id": target.node_id,
                "latency_ms": total_latency,
            })

        return self.events

    def _process_failures_up_to(self, current_time: float):
        """Inject any failures scheduled before current_time."""
        while (
            self._failure_idx < len(self._sorted_failures)
            and self._sorted_failures[self._failure_idx].time <= current_time
        ):
            fe = self._sorted_failures[self._failure_idx]
            self._failure_idx += 1

            # Determine which node failed
            failed_node = None
            if fe.target == "mfn" and self.mfn and self.mfn.is_alive:
                failed_node = self.mfn
            elif fe.target == "smfn" and self.smfn and self.smfn.is_alive:
                failed_node = self.smfn
            else:
                alive = [
                    n for n in self.env.fog_nodes
                    if n.is_alive and not n.is_mfn and not n.is_smfn
                ]
                if alive:
                    failed_node = alive[0]

            if failed_node is None:
                continue

            # Mark as failed
            failed_node.is_alive = False
            failed_node.failure_count += 1
            was_mfn = failed_node.is_mfn
            was_smfn = failed_node.is_smfn
            failed_node.is_mfn = False
            failed_node.is_smfn = False

            # Remove from busy tracking
            if failed_node.node_id in self._node_free_at:
                del self._node_free_at[failed_node.node_id]

            # ─── Recovery ───────────────────────────────────────────
            # Count in-flight tasks at failure time for state-dependent recovery
            in_flight = sum(n.queue_load for n in self.env.fog_nodes if n.is_alive)
            recovery_ms = self.scheme.handle_failure(
                self.env.fog_nodes, failed_node, in_flight
            )

            # During recovery, scheduling is paused
            self._recovery_until = max(
                self._recovery_until, fe.time + recovery_ms
            )

            # Re-elect coordinators
            alive = [n for n in self.env.fog_nodes if n.is_alive]
            if len(alive) >= 2:
                new_mfn, new_smfn = self.scheme.elect_coordinator(alive)
                for n in self.env.fog_nodes:
                    n.is_mfn = False
                    n.is_smfn = False
                if new_mfn:
                    new_mfn.is_mfn = True
                    self.mfn = new_mfn
                if new_smfn:
                    new_smfn.is_smfn = True
                    self.smfn = new_smfn
            elif len(alive) == 1:
                for n in self.env.fog_nodes:
                    n.is_mfn = False
                    n.is_smfn = False
                alive[0].is_mfn = True
                self.mfn = alive[0]
                self.smfn = None

            self.events.append({
                "type": "recovery",
                "time": fe.time,
                "failed_node": failed_node.node_id,
                "was_coordinator": was_mfn or was_smfn,
                "recovery_time": recovery_ms,
            })

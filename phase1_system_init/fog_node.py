"""
Fog Node
========
Represents a single distributed computing server in the fog layer.
Maintains runtime state Ψ(F_j) and provides telemetry reporting.

Implements Phase I — Step 3: Scheduling Infrastructure (Eq. 7–8).

    Ψ(F_j) = (Q_j, C_j, M_j, L_j, U_j)
    U_j^(0) = 1
"""

from __future__ import annotations

import random
import sys
import os
import time
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config


class FogNode:
    """
    A fog node with simulated resources and runtime telemetry.

    Parameters
    ----------
    node_id : str
        Unique identifier (e.g. "F_1", "F_2", ...).
    cpu : float
        Normalized computational capability C_j ∈ [0, 1].
    memory : float
        Normalized available memory M_j ∈ [0, 1].
    latency : float
        Communication latency L_j in ms.
    """

    def __init__(
        self,
        node_id: str,
        cpu: Optional[float] = None,
        memory: Optional[float] = None,
        latency: Optional[float] = None,
    ):
        self.node_id = node_id

        # Randomize within configured ranges if not specified
        self.cpu = cpu if cpu is not None else random.uniform(*config.CPU_RANGE)
        self.memory = (
            memory if memory is not None else random.uniform(*config.MEMORY_RANGE)
        )
        self.latency = (
            latency if latency is not None else random.uniform(*config.LATENCY_RANGE)
        )

        # Queue state
        self.queue: List[Any] = []
        self.queue_capacity = config.QUEUE_CAPACITY

        # Eq. 8:  U_j^(0) = 1  — initial trust score
        self.trust_score: float = 1.0

        # Historical tracking for stability assessment
        self.failure_count: int = 0
        self.total_tasks_executed: int = 0
        self.prev_coord_score: Optional[float] = None
        self.prev_sched_scores: Dict[str, float] = {}

        # Recovery-related state
        self.is_alive: bool = True
        self.last_heartbeat: float = time.time()
        self.cached_snapshot: Optional[Dict] = None
        self.cache_timestamp: Optional[float] = None

        # Role flags
        self.is_mfn: bool = False
        self.is_smfn: bool = False
        self.is_cache_node: bool = False

    # ─── Eq. 7:  Ψ(F_j) = (Q_j, C_j, M_j, L_j, U_j) ─────────────

    @property
    def queue_occupancy(self) -> float:
        """Normalized queue occupancy Q_j ∈ [0, 1]."""
        if self.queue_capacity == 0:
            return 1.0
        return len(self.queue) / self.queue_capacity

    @property
    def runtime_state(self) -> Dict[str, float]:
        """
        Return the full runtime state vector Ψ(F_j).
        """
        return {
            "Q_j": self.queue_occupancy,
            "C_j": self.cpu,
            "M_j": self.memory,
            "L_j": self.latency,
            "U_j": self.trust_score,
        }

    @property
    def failure_rate(self) -> float:
        """
        Normalized historical failure rate FR_j.
        """
        total = self.total_tasks_executed + self.failure_count
        if total == 0:
            return 0.0
        return self.failure_count / total

    # ─── Telemetry ──────────────────────────────────────────────────

    def report_telemetry(self) -> Dict[str, Any]:
        """
        Produce a telemetry report for the SMFN's global table.
        """
        return {
            "node_id": self.node_id,
            **self.runtime_state,
            "failure_rate": self.failure_rate,
            "is_alive": self.is_alive,
            "last_heartbeat": self.last_heartbeat,
        }

    def send_heartbeat(self):
        """Update the heartbeat timestamp."""
        self.last_heartbeat = time.time()

    # ─── Queue Management ──────────────────────────────────────────

    def enqueue(self, workload: Any) -> bool:
        """
        Add a workload to the processing queue.
        Returns False if the queue is full.
        """
        if len(self.queue) >= self.queue_capacity:
            return False
        self.queue.append(workload)
        return True

    def dequeue(self) -> Optional[Any]:
        """Remove and return the next workload from the queue."""
        if not self.queue:
            return None
        return self.queue.pop(0)

    def execute_workload(self, workload: Any) -> Dict[str, Any]:
        """
        Simulate workload execution.

        Returns a result dict with execution metadata.
        """
        self.total_tasks_executed += 1
        exec_time = random.uniform(0.01, 0.1)  # simulated processing
        result_data = os.urandom(64)  # simulated output
        return {
            "node_id": self.node_id,
            "workload_id": workload.get("BID", "unknown") if isinstance(workload, dict) else "unknown",
            "exec_time": exec_time,
            "result": result_data,
            "timestamp": time.time(),
        }

    # ─── Failure Simulation ────────────────────────────────────────

    def simulate_failure(self):
        """Mark this node as failed."""
        self.is_alive = False
        self.failure_count += 1

    def recover(self):
        """Bring a failed node back online."""
        self.is_alive = True
        self.send_heartbeat()

    # ─── Trust Update ──────────────────────────────────────────────

    def update_trust(self, success: bool, decay: float = 0.01):
        """
        Update trust score after task completion.

        Trust increases on success, decreases on failure,
        and is clamped to [0, 1].
        """
        if success:
            self.trust_score = min(1.0, self.trust_score + decay)
        else:
            self.trust_score = max(0.0, self.trust_score - decay * 5)

    def __repr__(self):
        role = ""
        if self.is_mfn:
            role = " [MFN]"
        elif self.is_smfn:
            role = " [SMFN]"
        elif self.is_cache_node:
            role = " [CACHE]"
        return (
            f"FogNode({self.node_id}{role}, "
            f"CPU={self.cpu:.2f}, MEM={self.memory:.2f}, "
            f"LAT={self.latency:.1f}ms, Q={self.queue_occupancy:.2f}, "
            f"U={self.trust_score:.2f})"
        )


def create_fog_infrastructure(
    n: int = config.NUM_FOG_NODES,
    seed: Optional[int] = None,
) -> List[FogNode]:
    """
    Create *n* fog nodes with randomized but reproducible resources.

    Parameters
    ----------
    n : int
        Number of fog nodes.
    seed : int, optional
        Random seed for reproducibility.
    """
    if seed is not None:
        random.seed(seed)

    nodes = []
    for i in range(1, n + 1):
        node = FogNode(
            node_id=f"F_{i}",
            cpu=random.uniform(*config.CPU_RANGE),
            memory=random.uniform(*config.MEMORY_RANGE),
            latency=random.uniform(*config.LATENCY_RANGE),
        )
        nodes.append(node)
    return nodes

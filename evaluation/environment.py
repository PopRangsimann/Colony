"""
Seeded Environment Generator
==============================
Produces a deterministic environment (fog nodes, workload trace,
failure schedule) from a single seed.  The same environment is
cloned for each scheme so that every scheme sees identical inputs.

SKILL.md Rule 2: One environment, one seed, all schemes.
"""

from __future__ import annotations

import copy
import random
import sys
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from evaluation import sim_config


@dataclass
class SimFogNode:
    """Lightweight fog node for simulation (no crypto dependencies)."""
    node_id: str
    cpu: float              # normalized computational capability [0, 1]
    memory: float           # normalized available memory [0, 1]
    latency: float          # communication latency (ms)
    queue_capacity: int = 100
    trust_score: float = 1.0
    failure_count: int = 0
    total_tasks: int = 0
    queue_load: int = 0     # current items in queue
    is_alive: bool = True
    is_mfn: bool = False
    is_smfn: bool = False
    is_cache_node: bool = False
    prev_coord_score: Optional[float] = None

    @property
    def queue_occupancy(self) -> float:
        return self.queue_load / max(self.queue_capacity, 1)

    @property
    def failure_rate(self) -> float:
        total = self.total_tasks + self.failure_count
        if total == 0:
            return 0.0
        return self.failure_count / total

    def processing_time(self, workload_size: float) -> float:
        """Simulated processing time in ms for a workload of given size."""
        if self.cpu <= 0:
            return 1e6
        return workload_size / (self.cpu * sim_config.WORKLOAD_PROCESSING_RATE)

    def comm_latency_ms(self) -> float:
        """Total communication latency including base overhead."""
        return self.latency + sim_config.BASE_COMM_LATENCY_MS


@dataclass
class Workload:
    """A single workload batch."""
    wid: int                # workload ID
    arrival_time: float     # simulated arrival time (ms)
    size: float             # normalized workload size [0.1, 1.0]
    deadline: float         # absolute deadline (ms)
    priority: float = 1.0   # application priority


@dataclass
class FailureEvent:
    """Scheduled coordinator failure."""
    time: float             # simulated time (ms) when failure occurs
    target: str             # "mfn" or "smfn"


@dataclass
class Environment:
    """
    Complete simulation environment.
    Clone this for each scheme to ensure identical inputs.
    """
    seed: int
    fog_nodes: List[SimFogNode]
    workloads: List[Workload]
    failure_events: List[FailureEvent]

    def clone(self) -> "Environment":
        """Deep copy so each scheme gets an independent state."""
        return Environment(
            seed=self.seed,
            fog_nodes=[copy.deepcopy(n) for n in self.fog_nodes],
            workloads=[copy.copy(w) for w in self.workloads],
            failure_events=[copy.copy(f) for f in self.failure_events],
        )


def build_environment(
    seed: int,
    num_fog_nodes: int = None,
    num_workloads: int = 500,
    inject_failures: bool = False,
    failure_interval_frac: float = None,
) -> Environment:
    """
    Build a seeded environment.

    Parameters
    ----------
    seed : int
        Random seed for reproducibility.
    num_fog_nodes : int
        Number of fog nodes.
    num_workloads : int
        Number of workload batches to generate.
    inject_failures : bool
        Whether to inject coordinator failures.
    failure_interval_frac : float
        Fraction of total time between failure injections.
    """
    rng = random.Random(seed)

    if num_fog_nodes is None:
        num_fog_nodes = sim_config.NUM_FOG_NODES_DEFAULT

    # ─── Generate fog nodes ────────────────────────────────────────
    nodes = []
    for i in range(num_fog_nodes):
        node = SimFogNode(
            node_id=f"F_{i+1}",
            cpu=rng.uniform(*config.CPU_RANGE),
            memory=rng.uniform(*config.MEMORY_RANGE),
            latency=rng.uniform(*config.LATENCY_RANGE),
            queue_capacity=config.QUEUE_CAPACITY,
        )
        nodes.append(node)

    # ─── Generate workload trace ───────────────────────────────────
    workloads = []
    time_cursor = 0.0
    for wid in range(num_workloads):
        # Inter-arrival time: exponential with mean based on rate
        inter_arrival = rng.expovariate(num_workloads / 5000.0)
        time_cursor += inter_arrival

        size = rng.uniform(0.1, 1.0)

        # Estimate processing time on an average node
        avg_cpu = sum(n.cpu for n in nodes) / len(nodes)
        est_processing = size / (avg_cpu * sim_config.WORKLOAD_PROCESSING_RATE)
        est_total = est_processing + rng.uniform(*config.LATENCY_RANGE)

        # Deadline = arrival + estimated_time * slack
        slack = rng.uniform(*sim_config.DEADLINE_SLACK_RANGE)
        deadline = time_cursor + est_total * slack * 1000  # convert to ms

        workloads.append(Workload(
            wid=wid,
            arrival_time=time_cursor,
            size=size,
            deadline=deadline,
            priority=rng.uniform(0.5, 2.0),
        ))

    # ─── Generate failure events ───────────────────────────────────
    failure_events = []
    if inject_failures and len(workloads) > 0:
        if failure_interval_frac is None:
            failure_interval_frac = sim_config.EXP4_FAILURE_INTERVAL_FRAC

        total_time = workloads[-1].arrival_time
        interval = total_time * failure_interval_frac
        t = interval
        while t < total_time * 0.9:  # don't inject in last 10%
            target = rng.choice(["mfn", "smfn"])
            failure_events.append(FailureEvent(time=t, target=target))
            t += interval

    return Environment(
        seed=seed,
        fog_nodes=nodes,
        workloads=workloads,
        failure_events=failure_events,
    )

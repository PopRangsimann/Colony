"""
Shared Metric Functions
========================
Identical metric definitions applied to every scheme.
SKILL.md Rule 4: schemes cannot override these definitions.
"""

from __future__ import annotations

from typing import Any, Dict, List
import numpy as np


def avg_completion_latency(events: List[Dict[str, Any]]) -> float:
    """
    Average workload completion latency (ms).

    Computed as mean(completion_time - arrival_time) over all
    completed workloads.
    """
    latencies = []
    for e in events:
        if e.get("completed", False):
            lat = e["completion_time"] - e["arrival_time"]
            latencies.append(lat)
    if not latencies:
        return 0.0
    return float(np.mean(latencies))


def recovery_latency(events: List[Dict[str, Any]]) -> float:
    """
    Average leadership recovery latency (ms).

    Measured as the time between failure detection and restoration
    of scheduling functionality.
    """
    recovery_times = []
    for e in events:
        if e.get("type") == "recovery":
            rt = e["recovery_time"]
            recovery_times.append(rt)
    if not recovery_times:
        return 0.0
    return float(np.mean(recovery_times))


def deadline_satisfaction_ratio(events: List[Dict[str, Any]]) -> float:
    """
    Percentage of workloads completed before their assigned deadline.
    """
    total = 0
    on_time = 0
    for e in events:
        if e.get("completed", False):
            total += 1
            if e["completion_time"] <= e["deadline"]:
                on_time += 1
    if total == 0:
        return 0.0
    return (on_time / total) * 100.0


def completion_ratio(events: List[Dict[str, Any]]) -> float:
    """
    Percentage of workloads successfully completed (regardless of deadline).
    """
    total = len(events)
    completed = sum(1 for e in events if e.get("completed", False))
    if total == 0:
        return 0.0
    return (completed / total) * 100.0

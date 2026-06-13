"""
Experiment 3: Deadline Satisfaction Under Overload
===================================================
X-axis: Workload arrival rate (increasing to saturation)
Y-axis: Deadline-satisfaction ratio (%)
Fixed:  8 fog nodes, no coordinator failures
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
from evaluation import sim_config
from evaluation.environment import build_environment
from evaluation.simulator import Simulator
from evaluation.metrics import deadline_satisfaction_ratio
from evaluation.schemes import SCHEME_REGISTRY


def run_exp3() -> dict:
    """Run Experiment 3 across all seeds and workload rates."""
    results = {name: {} for name in SCHEME_REGISTRY}

    for rate in sim_config.EXP3_WORKLOAD_RATES:
        print(f"  Exp3: rate={rate}")
        for name in SCHEME_REGISTRY:
            results[name][rate] = []

        for seed in sim_config.SEEDS:
            env = build_environment(
                seed=seed,
                num_fog_nodes=sim_config.EXP3_NUM_FOG_NODES,
                num_workloads=rate,
                inject_failures=sim_config.EXP3_INJECT_FAILURES,
            )

            for name, SchemeClass in SCHEME_REGISTRY.items():
                cloned = env.clone()
                scheme = SchemeClass()
                sim = Simulator(cloned, scheme)
                events = sim.run()
                dsr = deadline_satisfaction_ratio(events)
                results[name][rate].append(dsr)

    summary = {}
    for name in SCHEME_REGISTRY:
        summary[name] = {
            "x": sim_config.EXP3_WORKLOAD_RATES,
            "mean": [float(np.mean(results[name][r])) for r in sim_config.EXP3_WORKLOAD_RATES],
            "std": [float(np.std(results[name][r])) for r in sim_config.EXP3_WORKLOAD_RATES],
        }
    return summary

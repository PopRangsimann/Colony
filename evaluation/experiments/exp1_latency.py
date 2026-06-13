"""
Experiment 1: Workload Completion Latency
==========================================
X-axis: Workload arrival rate (100 → 10,000 batches)
Y-axis: Average workload completion latency (ms)
Fixed:  8 fog nodes, no failures
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
from evaluation import sim_config
from evaluation.environment import build_environment
from evaluation.simulator import Simulator
from evaluation.metrics import avg_completion_latency
from evaluation.schemes import SCHEME_REGISTRY


def run_exp1() -> dict:
    """Run Experiment 1 across all seeds and workload rates."""
    results = {name: {} for name in SCHEME_REGISTRY}

    for rate in sim_config.EXP1_WORKLOAD_RATES:
        print(f"  Exp1: rate={rate}")
        for name in SCHEME_REGISTRY:
            results[name][rate] = []

        for seed in sim_config.SEEDS:
            env = build_environment(
                seed=seed,
                num_fog_nodes=sim_config.EXP1_NUM_FOG_NODES,
                num_workloads=rate,
                inject_failures=sim_config.EXP1_INJECT_FAILURES,
            )

            for name, SchemeClass in SCHEME_REGISTRY.items():
                cloned = env.clone()
                scheme = SchemeClass()
                sim = Simulator(cloned, scheme)
                events = sim.run()
                lat = avg_completion_latency(events)
                results[name][rate].append(lat)

    # Compute mean and std
    summary = {}
    for name in SCHEME_REGISTRY:
        summary[name] = {
            "x": sim_config.EXP1_WORKLOAD_RATES,
            "mean": [float(np.mean(results[name][r])) for r in sim_config.EXP1_WORKLOAD_RATES],
            "std": [float(np.std(results[name][r])) for r in sim_config.EXP1_WORKLOAD_RATES],
        }
    return summary

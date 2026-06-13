"""
Experiment 2: Leadership Recovery Latency
==========================================
X-axis: Number of participating fog nodes (4 → 16)
Y-axis: Leadership recovery latency (ms)
Fixed:  Moderate workload rate, failures injected at consistent times
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
from evaluation import sim_config
from evaluation.environment import build_environment
from evaluation.simulator import Simulator
from evaluation.metrics import recovery_latency
from evaluation.schemes import SCHEME_REGISTRY


def run_exp2() -> dict:
    """Run Experiment 2 across all seeds and fog node counts."""
    results = {name: {} for name in SCHEME_REGISTRY}

    for n_nodes in sim_config.EXP2_FOG_NODE_COUNTS:
        print(f"  Exp2: nodes={n_nodes}")
        for name in SCHEME_REGISTRY:
            results[name][n_nodes] = []

        for seed in sim_config.SEEDS:
            env = build_environment(
                seed=seed,
                num_fog_nodes=n_nodes,
                num_workloads=sim_config.EXP2_WORKLOAD_RATE,
                inject_failures=True,
                failure_interval_frac=sim_config.EXP2_FAILURE_FRACTION,
            )

            for name, SchemeClass in SCHEME_REGISTRY.items():
                cloned = env.clone()
                scheme = SchemeClass()
                sim = Simulator(cloned, scheme)
                events = sim.run()
                rl = recovery_latency(events)
                results[name][n_nodes].append(rl)

    summary = {}
    for name in SCHEME_REGISTRY:
        summary[name] = {
            "x": sim_config.EXP2_FOG_NODE_COUNTS,
            "mean": [float(np.mean(results[name][n])) for n in sim_config.EXP2_FOG_NODE_COUNTS],
            "std": [float(np.std(results[name][n])) for n in sim_config.EXP2_FOG_NODE_COUNTS],
        }
    return summary

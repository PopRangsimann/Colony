"""
Experiment 4: System Resilience Under Combined Failures and Overload
=====================================================================
X-axis: Workload arrival rate (with simultaneous coordinator failures)
Y-axis: Successful workload-completion ratio (%)
Fixed:  8 fog nodes, failures injected throughout
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
from evaluation import sim_config
from evaluation.environment import build_environment
from evaluation.simulator import Simulator
from evaluation.metrics import completion_ratio
from evaluation.schemes import SCHEME_REGISTRY


def run_exp4() -> dict:
    """Run Experiment 4 across all seeds and workload rates with failures."""
    results = {name: {} for name in SCHEME_REGISTRY}

    for rate in sim_config.EXP4_WORKLOAD_RATES:
        print(f"  Exp4: rate={rate}")
        for name in SCHEME_REGISTRY:
            results[name][rate] = []

        for seed in sim_config.SEEDS:
            env = build_environment(
                seed=seed,
                num_fog_nodes=sim_config.EXP4_NUM_FOG_NODES,
                num_workloads=rate,
                inject_failures=True,
                failure_interval_frac=sim_config.EXP4_FAILURE_INTERVAL_FRAC,
            )

            for name, SchemeClass in SCHEME_REGISTRY.items():
                cloned = env.clone()
                scheme = SchemeClass()
                sim = Simulator(cloned, scheme)
                events = sim.run()
                cr = completion_ratio(events)
                results[name][rate].append(cr)

    summary = {}
    for name in SCHEME_REGISTRY:
        summary[name] = {
            "x": sim_config.EXP4_WORKLOAD_RATES,
            "mean": [float(np.mean(results[name][r])) for r in sim_config.EXP4_WORKLOAD_RATES],
            "std": [float(np.std(results[name][r])) for r in sim_config.EXP4_WORKLOAD_RATES],
        }
    return summary

"""
Run All Experiments
====================
Executes all 4 experiments, generates CSV data and PNG figures.

Usage:
    python3 -m evaluation.run_all
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from evaluation.experiments.exp1_latency import run_exp1
from evaluation.experiments.exp2_recovery import run_exp2
from evaluation.experiments.exp3_deadline import run_exp3
from evaluation.experiments.exp4_resilience import run_exp4
from evaluation.plotting import plot_experiment


def main():
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Colony — Performance Evaluation Simulation                 ║")
    print("║  4 experiments × 4 schemes × 20 seeds                      ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    total_start = time.time()

    # ─── Experiment 1: Workload Completion Latency ─────────────────
    print("\n[Experiment 1] Workload Completion Latency")
    t0 = time.time()
    exp1 = run_exp1()
    plot_experiment(
        exp1,
        title="Average Workload Completion Latency",
        xlabel="Number of Workload Batches",
        ylabel="Avg. Completion Latency (ms)",
        filename="fig2_latency",
        logx=True,
    )
    print(f"  Done in {time.time()-t0:.1f}s")

    # ─── Experiment 2: Leadership Recovery Latency ─────────────────
    print("\n[Experiment 2] Leadership Recovery Latency")
    t0 = time.time()
    exp2 = run_exp2()
    plot_experiment(
        exp2,
        title="Leadership Recovery Latency",
        xlabel="Number of Fog Nodes",
        ylabel="Recovery Latency (ms)",
        filename="fig3_recovery",
        ylim=(0, None),
    )
    print(f"  Done in {time.time()-t0:.1f}s")

    # ─── Experiment 3: Deadline Satisfaction ────────────────────────
    print("\n[Experiment 3] Deadline Satisfaction Under Overload")
    t0 = time.time()
    exp3 = run_exp3()
    plot_experiment(
        exp3,
        title="Deadline-Satisfaction Ratio Under Overload",
        xlabel="Number of Workload Batches",
        ylabel="Deadline Satisfaction (%)",
        filename="fig4_deadline",
        logx=True,
        ylim=(0, 105),
    )
    print(f"  Done in {time.time()-t0:.1f}s")

    # ─── Experiment 4: System Resilience ───────────────────────────
    print("\n[Experiment 4] System Resilience Under Combined Failures")
    t0 = time.time()
    exp4 = run_exp4()
    plot_experiment(
        exp4,
        title="Workload Completion Ratio Under Combined Failures",
        xlabel="Number of Workload Batches",
        ylabel="Completion Ratio (%)",
        filename="fig5_resilience",
        logx=True,
        ylim=(80, 101),
    )
    print(f"  Done in {time.time()-t0:.1f}s")

    total = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"  All experiments complete in {total:.1f}s")
    print(f"  Results saved to evaluation/results/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

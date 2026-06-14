"""
Recovery Time Benchmark
========================
Measures REAL recovery times from the Phase IV/VI prototype code
and feeds measured values into sim_config.py.

Colony recovery = build snapshot + replicate + restore from snapshot
Baseline recovery = full re-election from scratch (Level 3)

Runs 1000 iterations to get stable averages.
"""

import sys
import os
import time
import json
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from phase4_load_balancing.coordinator_election import (
    elect_coordinators,
    compute_coordination_score,
    apply_stability_penalty,
)
from phase4_load_balancing.state_replication import (
    build_scheduling_snapshot,
    compute_recovery_score,
    replicate_to_cache_nodes,
)
from phase4_load_balancing.fri import compute_fri
from phase6_recovery_and_results.leadership_recovery import LeadershipRecovery

# ─── Use the same FogNode class from run_all_phases.py ─────────────

from phase1_system_init.fog_node import create_fog_infrastructure as create_fog_nodes


def measure_colony_recovery(fog_nodes, n_iterations=1000):
    """
    Measure Colony's Level 1 + Level 2 recovery times.
    
    Colony recovery process:
    1. Build snapshot (Eq. 31)
    2. Replicate to cache nodes
    3. On failure: load snapshot + select new MFN (Eq. 43-44)
    """
    level1_times = []
    level2_times = []
    snapshot_build_times = []
    replication_times = []

    for _ in range(n_iterations):
        # Reset nodes
        for n in fog_nodes:
            n.is_alive = True
            n.is_mfn = False
            n.is_smfn = False
            n.prev_coord_score = None
            n.cached_snapshot = None
            n.cache_timestamp = None

        # Elect coordinators
        mfn, smfn, _ = elect_coordinators(fog_nodes)

        # Step 1: Build snapshot (this is the state that gets replicated)
        t0 = time.perf_counter_ns()
        snapshot = build_scheduling_snapshot(
            epoch=1, mfn=mfn, smfn=smfn, fog_nodes=fog_nodes
        )
        t1 = time.perf_counter_ns()
        snapshot_build_times.append((t1 - t0) / 1e6)  # ns → ms

        # Step 2: Replicate to cache nodes
        t0 = time.perf_counter_ns()
        cache_nodes = replicate_to_cache_nodes(snapshot, fog_nodes, n_cache=3)
        t1 = time.perf_counter_ns()
        replication_times.append((t1 - t0) / 1e6)

        # ─── Level 1 Recovery: SMFN takes over ────────────────────────
        # Simulate MFN failure
        mfn.is_alive = False
        mfn.is_mfn = False

        recovery = LeadershipRecovery()
        t0 = time.perf_counter_ns()
        new_mfn, new_smfn = recovery.level1_recovery(smfn, fog_nodes)
        t1 = time.perf_counter_ns()
        level1_times.append((t1 - t0) / 1e6)

        # Restore for Level 2 test
        mfn.is_alive = True
        for n in fog_nodes:
            n.is_mfn = False
            n.is_smfn = False
        mfn, smfn, _ = elect_coordinators(fog_nodes)
        cache_nodes = replicate_to_cache_nodes(snapshot, fog_nodes, n_cache=3)

        # ─── Level 2 Recovery: Both MFN + SMFN fail ──────────────────
        mfn.is_alive = False
        smfn.is_alive = False
        mfn.is_mfn = False
        smfn.is_smfn = False

        recovery2 = LeadershipRecovery()
        t0 = time.perf_counter_ns()
        new_mfn2, new_smfn2 = recovery2.level2_recovery(cache_nodes, fog_nodes)
        t1 = time.perf_counter_ns()
        level2_times.append((t1 - t0) / 1e6)

        # Restore
        mfn.is_alive = True
        smfn.is_alive = True

    return {
        "snapshot_build_ms": snapshot_build_times,
        "replication_ms": replication_times,
        "level1_recovery_ms": level1_times,
        "level2_recovery_ms": level2_times,
    }


def measure_baseline_reelection(fog_nodes, n_iterations=1000):
    """
    Measure baseline recovery = full re-election (Level 3).
    
    This is what Ref[3], Ref[6], Ref[20] do: they don't have
    pre-replicated state, so they must run a full coordinator
    election from scratch.
    """
    reelection_times = []

    for _ in range(n_iterations):
        # Reset all nodes
        for n in fog_nodes:
            n.is_alive = True
            n.is_mfn = False
            n.is_smfn = False
            n.prev_coord_score = None

        # Simulate: one node fails, must re-elect from scratch
        fog_nodes[0].is_alive = False

        t0 = time.perf_counter_ns()
        mfn, smfn, scores = elect_coordinators(fog_nodes)
        t1 = time.perf_counter_ns()
        reelection_times.append((t1 - t0) / 1e6)

        fog_nodes[0].is_alive = True

    return {"full_reelection_ms": reelection_times}


def measure_baseline_reelection_scaling(n_iterations=500):
    """
    Measure how re-election time scales with number of fog nodes.
    """
    results = {}
    for n_nodes in [4, 6, 8, 10, 12, 14, 16]:
        nodes = create_fog_nodes(n_nodes)
        times = []
        for _ in range(n_iterations):
            for n in nodes:
                n.is_alive = True
                n.is_mfn = False
                n.is_smfn = False
                n.prev_coord_score = None
            nodes[0].is_alive = False

            t0 = time.perf_counter_ns()
            mfn, smfn, scores = elect_coordinators(nodes)
            t1 = time.perf_counter_ns()
            times.append((t1 - t0) / 1e6)

            nodes[0].is_alive = True

        results[n_nodes] = {
            "mean_ms": statistics.mean(times),
            "std_ms": statistics.stdev(times) if len(times) > 1 else 0,
            "min_ms": min(times),
            "max_ms": max(times),
        }
    return results


def print_stats(name, values):
    """Print summary statistics for a list of timing values."""
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0
    p50 = statistics.median(values)
    p99 = sorted(values)[int(len(values) * 0.99)]
    print(f"  {name:30s}: mean={mean:.4f}ms  std={std:.4f}ms  "
          f"p50={p50:.4f}ms  p99={p99:.4f}ms  min={min(values):.4f}ms  max={max(values):.4f}ms")


def main():
    print("=" * 70)
    print("  Recovery Time Benchmark (1000 iterations)")
    print("=" * 70)

    # Create 8 fog nodes (same as evaluation)
    fog_nodes = create_fog_nodes(8)
    
    print("\n─── Colony Recovery (from pre-replicated snapshot) ───")
    colony = measure_colony_recovery(fog_nodes, n_iterations=1000)
    print_stats("Snapshot build", colony["snapshot_build_ms"])
    print_stats("Replication to 3 caches", colony["replication_ms"])
    print_stats("Level 1 (SMFN takeover)", colony["level1_recovery_ms"])
    print_stats("Level 2 (cache node promotion)", colony["level2_recovery_ms"])

    total_colony = [
        colony["level1_recovery_ms"][i]  # recovery itself
        for i in range(len(colony["level1_recovery_ms"]))
    ]
    print_stats("TOTAL Colony recovery (Level 1)", total_colony)

    print("\n─── Baseline Recovery (full re-election) ───")
    baseline = measure_baseline_reelection(fog_nodes, n_iterations=1000)
    print_stats("Full re-election (8 nodes)", baseline["full_reelection_ms"])

    print("\n─── Baseline Re-election Scaling ───")
    scaling = measure_baseline_reelection_scaling(n_iterations=500)
    for n_nodes, stats in sorted(scaling.items()):
        print(f"  {n_nodes:2d} nodes: mean={stats['mean_ms']:.4f}ms  "
              f"std={stats['std_ms']:.4f}ms  "
              f"min={stats['min_ms']:.4f}ms  max={stats['max_ms']:.4f}ms")

    print("\n─── Ratio ───")
    colony_mean = statistics.mean(colony["level1_recovery_ms"])
    baseline_mean = statistics.mean(baseline["full_reelection_ms"])
    print(f"  Colony Level 1:     {colony_mean:.4f}ms")
    print(f"  Baseline re-elect:  {baseline_mean:.4f}ms")
    print(f"  Speedup:            {baseline_mean/colony_mean:.1f}×")

    # Save raw data
    output = {
        "colony_level1_mean_ms": statistics.mean(colony["level1_recovery_ms"]),
        "colony_level2_mean_ms": statistics.mean(colony["level2_recovery_ms"]),
        "colony_snapshot_build_mean_ms": statistics.mean(colony["snapshot_build_ms"]),
        "colony_replication_mean_ms": statistics.mean(colony["replication_ms"]),
        "baseline_reelection_mean_ms": baseline_mean,
        "scaling": scaling,
    }
    
    out_path = os.path.join(os.path.dirname(__file__), "..", "evaluation", "results", "data", "recovery_benchmark.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Saved raw data to: {out_path}")


if __name__ == "__main__":
    main()

"""
Phase IV: Stability-Aware Load Balancing — Demonstration
=========================================================
Elects MFN/SMFN, computes FRI, schedules workloads, and replicates
recovery state to cache nodes.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from phase3_workload_profiling.demo import run_phase3
from phase4_load_balancing.coordinator_election import elect_coordinators
from phase4_load_balancing.fri import compute_fri
from phase4_load_balancing.scheduler import assign_workload
from phase4_load_balancing.state_replication import (
    build_scheduling_snapshot,
    compute_recovery_score,
    replicate_to_cache_nodes,
)


def run_phase4(phase3_ctx=None):
    """Execute Phase IV using Phase III context."""
    if phase3_ctx is None:
        phase3_ctx = run_phase3()

    print("\n" + "=" * 70)
    print("  PHASE IV: Stability-Aware Load Balancing")
    print("=" * 70)

    fog_nodes = phase3_ctx["fog_nodes"]
    workload_profile = phase3_ctx["workload_profile"]
    batch = phase3_ctx["batch"]

    # ─── Step 1: Coordinator Election ──────────────────────────────
    print("\n[Step 1] Stability-Aware Coordinator Election")
    mfn, smfn, coord_scores = elect_coordinators(fog_nodes)
    print(f"  MFN:  {mfn.node_id} (score={coord_scores[mfn.node_id]['penalized']:.4f})")
    print(f"  SMFN: {smfn.node_id} (score={coord_scores[smfn.node_id]['penalized']:.4f})")
    print(f"\n  All coordination scores:")
    for nid, s in sorted(coord_scores.items(), key=lambda x: x[1]["penalized"], reverse=True):
        print(f"    {nid}: raw={s['raw']:.4f}  penalized={s['penalized']:.4f}")

    # ─── Step 2: Failure Resilience Assessment ─────────────────────
    print("\n[Step 2] Failure Resilience Index (FRI)")
    fri_values = {}
    for node in fog_nodes:
        fri = compute_fri(node)
        fri_values[node.node_id] = fri
        print(f"    {node.node_id}: FRI={fri:.4f}")

    # ─── Step 3: Recovery-Aware Workload Scheduling ────────────────
    print("\n[Step 3] Recovery-Aware Workload Scheduling")
    best_node, sched_scores = assign_workload(
        fog_nodes, workload_profile, batch_id=batch["BID"]
    )
    print(f"  Assigned batch {batch['BID']} → {best_node.node_id}")
    print(f"\n  Scheduling scores (lower = better):")
    for nid, s in sorted(sched_scores.items(), key=lambda x: x[1]["smoothed"]):
        marker = " ← SELECTED" if nid == best_node.node_id else ""
        print(f"    {nid}: raw={s['raw']:.4f}  smoothed={s['smoothed']:.4f}{marker}")

    # Simulate workload execution
    best_node.enqueue(batch)
    exec_result = best_node.execute_workload(best_node.dequeue())

    # ─── Step 4: Recovery-State Maintenance ────────────────────────
    print("\n[Step 4] Recovery-State Maintenance")
    snapshot = build_scheduling_snapshot(
        epoch=1, mfn=mfn, smfn=smfn, fog_nodes=fog_nodes
    )
    print(f"  Built snapshot: epoch={snapshot['epoch']}, "
          f"telemetry entries={len(snapshot['telemetry'])}")

    cache_nodes = replicate_to_cache_nodes(snapshot, fog_nodes)
    print(f"  Replicated to {len(cache_nodes)} cache nodes:")
    for cn in cache_nodes:
        rs = compute_recovery_score(cn)
        print(f"    {cn.node_id}: RS={rs:.4f}")

    print("\n  Phase IV Complete ✓")

    return {
        **phase3_ctx,
        "mfn": mfn,
        "smfn": smfn,
        "cache_nodes": cache_nodes,
        "snapshot": snapshot,
        "fri_values": fri_values,
        "assigned_node": best_node,
        "exec_result": exec_result,
    }


if __name__ == "__main__":
    run_phase4()

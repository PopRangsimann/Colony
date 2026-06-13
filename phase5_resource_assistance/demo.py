"""
Phase V: Recovery-Preserving Collaborative Resource Assistance — Demo
======================================================================
Simulates an overloaded workload, recruits helper nodes, partitions
work, and combines results.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from phase4_load_balancing.demo import run_phase4
from phase5_resource_assistance.assistance_request import (
    check_assistance_needed,
    compute_resource_deficit,
    generate_request,
)
from phase5_resource_assistance.helper_selection import (
    compute_recovery_capability,
    select_helpers,
)
from phase5_resource_assistance.collaborative import (
    compute_assistance_budget,
    partition_workload,
    combine_results,
)


def run_phase5(phase4_ctx=None):
    """Execute Phase V using Phase IV context."""
    if phase4_ctx is None:
        phase4_ctx = run_phase4()

    print("\n" + "=" * 70)
    print("  PHASE V: Recovery-Preserving Collaborative Resource Assistance")
    print("=" * 70)

    fog_nodes = phase4_ctx["fog_nodes"]
    workload_profile = phase4_ctx["workload_profile"]
    batch = phase4_ctx["batch"]
    assigned_node = phase4_ctx["assigned_node"]

    # ─── Step 1: Assistance Request Generation ─────────────────────
    print("\n[Step 1] Assistance Request Generation")

    # Simulate an overload scenario: estimated time exceeds deadline
    t_est = time.time() + 10.0  # estimated: 10 seconds from now
    t_deadline = workload_profile["deadline"]

    needs_help = check_assistance_needed(
        t_est=t_est,
        t_deadline=t_deadline,
        delta_k=workload_profile["delta_k"],
        rho_k=workload_profile["rho_k"],
    )
    print(f"  Hosting node:      {assigned_node.node_id}")
    print(f"  T_est:             {t_est:.3f}")
    print(f"  T_deadline:        {t_deadline:.3f}")
    print(f"  Assistance needed: {needs_help}")

    # Compute resource deficit
    c_required = 0.8  # simulated requirement
    c_available = assigned_node.cpu * (1.0 - assigned_node.queue_occupancy)
    delta_c = compute_resource_deficit(c_required, c_available)
    print(f"  C_required:        {c_required:.3f}")
    print(f"  C_available:       {c_available:.3f}")
    print(f"  ΔC_k:              {delta_c:.3f}")

    ar_k = generate_request(batch, delta_c, workload_profile["delta_k"], workload_profile["rho_k"])
    print(f"  AR_k generated for batch {ar_k['BID']}")

    # ─── Step 2: Recovery-Preserving Helper Selection ──────────────
    print("\n[Step 2] Recovery-Preserving Helper Selection")

    helpers, all_scores = select_helpers(
        fog_nodes, assigned_node, delta_c
    )

    print(f"  Helper candidates scored:")
    for nid, sc in sorted(all_scores.items(), key=lambda x: x[1]["HScore"], reverse=True):
        marker = " ← SELECTED" if any(h.node_id == nid for h in helpers) else ""
        print(f"    {nid}: HScore={sc['HScore']:.4f}, RC={sc['RC']:.4f}, "
              f"avail={sc['available']:.3f}{marker}")

    print(f"\n  Selected {len(helpers)} helpers: {[h.node_id for h in helpers]}")

    # Show RC vs τ_R analysis
    from phase5_resource_assistance.helper_selection import compute_recovery_capability
    import config
    print(f"\n  Recovery capability analysis (τ_R = {config.TAU_R}):")
    for node in fog_nodes:
        if node.is_mfn or node.is_smfn:
            continue
        rc = compute_recovery_capability(node)
        status = "RESERVED" if rc >= config.TAU_R else "available"
        print(f"    {node.node_id}: RC={rc:.4f} → {status}")

    # ─── Step 3: Collaborative Assistance and Aggregation ──────────
    print("\n[Step 3] Collaborative Assistance and Aggregation")

    # Compute assistance budgets
    budgets = {}
    for h in helpers:
        ab = compute_assistance_budget(h)
        budgets[h.node_id] = ab
        print(f"    {h.node_id}: AB={ab:.4f}")

    # Partition workload
    partitions = partition_workload(helpers, delta_c)
    print(f"\n  Workload partitions (ΔC_k = {delta_c:.3f}):")
    for nid, w in partitions.items():
        print(f"    {nid}: W_i = {w:.4f}")

    # Simulate helper execution
    partial_results = []
    for h in helpers:
        result = h.execute_workload({"BID": batch["BID"], "type": "helper_fragment"})
        partial_results.append(result)

    # Combine results
    combined = combine_results(partial_results)
    print(f"\n  Combined result:")
    print(f"    Fragments:       {combined['fragments']}")
    print(f"    Total exec time: {combined['total_exec_time']:.4f}s")
    print(f"    Participating:   {combined['node_ids']}")

    print("\n  Phase V Complete ✓")

    return {
        **phase4_ctx,
        "helpers": helpers,
        "partitions": partitions,
        "combined_result": combined,
    }


if __name__ == "__main__":
    run_phase5()

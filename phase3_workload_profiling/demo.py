"""
Phase III: Scheduling-Aware Workload Profiling — Demonstration
===============================================================
Validates packets, forms micro-batches, and profiles workloads.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from phase2_iiot_protection.demo import run_phase2
from phase3_workload_profiling.gateway import EdgeGateway


def run_phase3(phase2_ctx=None):
    """Execute Phase III using Phase II context."""
    if phase2_ctx is None:
        phase2_ctx = run_phase2()

    print("\n" + "=" * 70)
    print("  PHASE III: Scheduling-Aware Workload Profiling")
    print("=" * 70)

    packets = phase2_ctx["packets"]
    iiot_devices = phase2_ctx["iiot_devices"]

    # Build device_keys map (device_id -> K_base) for gateway validation
    device_keys = {
        dev_id: dev.k_base
        for dev_id, dev in iiot_devices.items()
    }

    gateway = EdgeGateway(device_keys)

    # Process all packets in a single batch
    print(f"\n  Incoming packets: {len(packets)}")
    result = gateway.process_incoming(packets, app_priority=1.0)

    if result is None:
        print("  ERROR: No valid packets!")
        return phase2_ctx

    batch, profile = result

    print(f"\n[Step 1] Packet Validation")
    print(f"  Valid packets:   {batch['size']}")
    print(f"  Batch ID:        {batch['BID']}")
    print(f"  GTag:            {batch['GTag'][:16].hex()}...")

    print(f"\n[Step 2] Micro-Batch Formation")
    print(f"  Batch size S_k:  {batch['size']}")
    print(f"  Packet hashes:   {len(batch['packet_hashes'])}")

    print(f"\n[Step 3] Workload Profiling — Φ(B_k)")
    print(f"  S_k (batch size):         {profile['S_k']}")
    print(f"  V_k (payload volume):     {profile['V_k']:.2f} KB")
    print(f"  D_k (complexity):         {profile['D_k']:.3f}")
    print(f"  ω_k (intensity):          {profile['omega_k']:.3f}")
    print(f"  δ_k (deadline urgency):   {profile['delta_k']:.3f}")
    print(f"  ρ_k (recovery priority):  {profile['rho_k']:.3f}")
    print(f"  Deadline:                 {profile['deadline']:.3f}")

    # Test replay rejection — re-submit the same packets
    print(f"\n[Replay Test] Re-submitting same packets...")
    result2 = gateway.process_incoming(packets, app_priority=1.0)
    if result2 is None:
        print("  All replayed packets rejected ✓")
    else:
        _, profile2 = result2
        print(f"  WARNING: {profile2['S_k']} packets accepted (should be 0)")

    print("\n  Phase III Complete ✓")

    return {
        **phase2_ctx,
        "gateway": gateway,
        "batch": batch,
        "workload_profile": profile,
    }


if __name__ == "__main__":
    run_phase3()

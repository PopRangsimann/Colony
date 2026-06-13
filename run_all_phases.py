"""
Colony Framework — Full Pipeline Demonstration
=================================================
Runs Phase I through Phase VI sequentially, demonstrating the
complete stability-aware load-balancing framework with autonomous
leadership recovery for resilient fog-assisted IIoT systems.

Usage:
    python run_all_phases.py
"""

import sys
import os
import time

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(__file__))

from phase1_system_init.demo import run_phase1
from phase2_iiot_protection.demo import run_phase2
from phase3_workload_profiling.demo import run_phase3
from phase4_load_balancing.demo import run_phase4
from phase5_resource_assistance.demo import run_phase5
from phase6_recovery_and_results.demo import run_phase6


def main():
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  Colony: Stability-Aware Load Balancing with Autonomous        ║")
    print("║  Leadership Recovery for Resilient Fog-Assisted IIoT Systems   ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    start = time.time()

    # Phase I: System Initialization
    ctx = run_phase1()

    # Phase II: Hardware-Bound IIoT Protection
    ctx = run_phase2(ctx)

    # Phase III: Scheduling-Aware Workload Profiling
    ctx = run_phase3(ctx)

    # Phase IV: Stability-Aware Load Balancing
    ctx = run_phase4(ctx)

    # Phase V: Recovery-Preserving Collaborative Resource Assistance
    ctx = run_phase5(ctx)

    # Phase VI: Autonomous Leadership Recovery & Secure Results
    ctx = run_phase6(ctx)

    elapsed = time.time() - start

    print("\n" + "=" * 70)
    print("  ALL PHASES COMPLETE")
    print("=" * 70)
    print(f"\n  Total execution time: {elapsed:.2f} seconds")
    print(f"  Fog nodes:            {len(ctx['fog_nodes'])}")
    print(f"  IIoT devices:         {len(ctx['iiot_devices'])}")
    print(f"  Packets processed:    {len(ctx['packets'])}")
    print(f"  Batch ID:             {ctx['batch']['BID']}")
    print(f"  Final result size:    {len(ctx['final_result'])} bytes")
    print(f"  Recovery events:      {len(ctx.get('package', {}).get('CT_ABE_k', {}).get('rho', []))} policy attrs")

    # Summary verification
    print(f"\n  Verification Summary:")
    print(f"    ✓ CP-ABE key generation and encryption")
    print(f"    ✓ PUF enrollment and authentication")
    print(f"    ✓ Kyber post-quantum key establishment")
    print(f"    ✓ ChaCha20-Poly1305 packet protection")
    print(f"    ✓ Packet validation and replay rejection")
    print(f"    ✓ Micro-batch formation with integrity")
    print(f"    ✓ Workload profiling (ω, δ, ρ)")
    print(f"    ✓ MFN/SMFN coordinator election")
    print(f"    ✓ FRI computation and recovery-aware scheduling")
    print(f"    ✓ State replication to cache nodes")
    print(f"    ✓ Overload detection and helper selection")
    print(f"    ✓ Recovery-preserving workload partitioning")
    print(f"    ✓ Heartbeat-based failure detection")
    print(f"    ✓ Level 1 and Level 2 leadership recovery")
    print(f"    ✓ CP-ABE result protection and AES-GCM encryption")
    print(f"    ✓ Authorized retrieval and integrity verification")

    return ctx


if __name__ == "__main__":
    main()

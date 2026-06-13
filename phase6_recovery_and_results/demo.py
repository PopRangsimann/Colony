"""
Phase VI: Autonomous Leadership Recovery & Secure Result Management — Demo
===========================================================================
Demonstrates failure detection, autonomous recovery, result protection
with CP-ABE, and authorized result retrieval.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from phase5_resource_assistance.demo import run_phase5
from phase6_recovery_and_results.failure_detection import HeartbeatMonitor
from phase6_recovery_and_results.leadership_recovery import LeadershipRecovery
from phase6_recovery_and_results.result_manager import ResultManager
from phase6_recovery_and_results.result_retrieval import ResultRetrieval


def run_phase6(phase5_ctx=None):
    """Execute Phase VI using Phase V context."""
    if phase5_ctx is None:
        phase5_ctx = run_phase5()

    print("\n" + "=" * 70)
    print("  PHASE VI: Autonomous Leadership Recovery & Secure Result Management")
    print("=" * 70)

    fog_nodes = phase5_ctx["fog_nodes"]
    mfn = phase5_ctx["mfn"]
    smfn = phase5_ctx["smfn"]
    cache_nodes = phase5_ctx["cache_nodes"]
    combined_result = phase5_ctx["combined_result"]
    batch = phase5_ctx["batch"]
    aa = phase5_ctx["aa"]
    exec_result = phase5_ctx["exec_result"]

    # ─── Step 1: Coordinator Failure Detection ─────────────────────
    print("\n[Step 1] Coordinator Failure Detection")
    monitor = HeartbeatMonitor()

    # All alive initially
    mfn.send_heartbeat()
    smfn.send_heartbeat()
    status = monitor.detect_failures(mfn, smfn)
    print(f"  MFN ({status['mfn_id']}):  alive={status['mfn_alive']}")
    print(f"  SMFN ({status['smfn_id']}): alive={status['smfn_alive']}")

    # Simulate MFN failure (set last heartbeat far in the past)
    print(f"\n  Simulating MFN failure...")
    mfn.last_heartbeat = time.time() - 10.0  # 10 seconds ago
    status = monitor.detect_failures(mfn, smfn)
    print(f"  MFN ({status['mfn_id']}):  alive={status['mfn_alive']}")
    print(f"  SMFN ({status['smfn_id']}): alive={status['smfn_alive']}")

    # ─── Step 2: Autonomous Leadership Recovery ────────────────────
    print("\n[Step 2] Autonomous Leadership Recovery")
    recovery = LeadershipRecovery()

    new_mfn, new_smfn, level = recovery.recover(
        mfn_alive=status["mfn_alive"],
        smfn_alive=status["smfn_alive"],
        mfn=mfn,
        smfn=smfn,
        cache_nodes=cache_nodes,
        fog_nodes=fog_nodes,
    )
    print(f"  Recovery level: {level}")
    print(f"  New MFN:  {new_mfn.node_id}")
    print(f"  New SMFN: {new_smfn.node_id if new_smfn else 'None'}")

    # Test Level 2 recovery (both fail)
    print(f"\n  Simulating both MFN and SMFN failure...")
    new_mfn.last_heartbeat = time.time() - 10.0
    if new_smfn:
        new_smfn.last_heartbeat = time.time() - 10.0

    status2 = monitor.detect_failures(new_mfn, new_smfn or new_mfn)
    new_mfn2, new_smfn2, level2 = recovery.recover(
        mfn_alive=status2["mfn_alive"],
        smfn_alive=status2["smfn_alive"],
        mfn=new_mfn,
        smfn=new_smfn or new_mfn,
        cache_nodes=cache_nodes,
        fog_nodes=fog_nodes,
    )
    print(f"  Recovery level: {level2}")
    print(f"  New MFN:  {new_mfn2.node_id}")
    print(f"  New SMFN: {new_smfn2.node_id if new_smfn2 else 'None'}")

    print(f"\n  Recovery log: {len(recovery.recovery_log)} events")
    for entry in recovery.recovery_log:
        print(f"    Level {entry['level']}: MFN→{entry['new_mfn']}, SMFN→{entry['new_smfn']}")

    # ─── Step 3: Result Aggregation ────────────────────────────────
    print("\n[Step 3] Result Aggregation")
    cpabe = aa.get_cpabe()
    result_mgr = ResultManager(cpabe, aa.mpk)

    # Aggregate from the execution result and combined helper results
    all_results = [exec_result, combined_result]
    final_result = result_mgr.aggregate_results(all_results)
    print(f"  Aggregated result size: {len(final_result)} bytes")

    # ─── Step 4: Secure Result Protection ──────────────────────────
    print("\n[Step 4] Secure Result Protection & Outsourcing")
    package = result_mgr.protect_result(
        result=final_result,
        batch_id=batch["BID"],
        access_policy={"type": "AND", "attributes": ["Engineer", "Supervisor"]},
    )
    print(f"  CT_k:     {len(package['CT_k'])} bytes (AES-GCM encrypted)")
    print(f"  CT_ABE_k: CP-ABE ciphertext with {len(package['CT_ABE_k'].get('rho', []))} attributes")
    print(f"  H_k:      {package['H_k'][:16].hex()}...")

    # Outsource to cloud
    storage_key = result_mgr.outsource_to_cloud(package)
    print(f"  Outsourced to cloud with key: {storage_key}")

    # ─── Step 5: Authorized Result Retrieval ───────────────────────
    print("\n[Step 5] Authorized Result Retrieval")
    retrieval = ResultRetrieval(cpabe)

    # Test with authorized user (Alice: Engineer + Supervisor)
    sk_alice = aa.user_keys["user_alice"]
    retrieved = result_mgr.retrieve_from_cloud(batch["BID"])

    result_data, integrity_ok = retrieval.retrieve_and_verify(
        retrieved, sk_alice
    )

    if result_data is not None:
        print(f"  user_alice (Engineer, Supervisor):")
        print(f"    Decryption:  SUCCESS ({len(result_data)} bytes)")
        print(f"    Integrity:   {'VERIFIED ✓' if integrity_ok else 'FAILED ✗'}")
        print(f"    Data match:  {result_data == final_result}")
    else:
        print(f"  user_alice: Decryption FAILED")

    # Test with unauthorized user (Bob: Operator, Analyst — wrong attributes)
    sk_bob = aa.user_keys["user_bob"]
    result_bob, integrity_bob = retrieval.retrieve_and_verify(
        retrieved, sk_bob
    )
    print(f"\n  user_bob (Operator, Analyst):")
    if result_bob is None:
        print(f"    Decryption:  DENIED (attributes don't satisfy policy) ✓")
    else:
        print(f"    Decryption:  Unexpectedly succeeded")

    print("\n  Phase VI Complete ✓")

    return {
        **phase5_ctx,
        "final_result": final_result,
        "package": package,
        "result_manager": result_mgr,
    }


if __name__ == "__main__":
    run_phase6()

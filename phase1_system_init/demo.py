"""
Phase I: System Initialization — Demonstration
===============================================
Sets up the complete security, communication, and scheduling
infrastructure:
  1. CP-ABE Setup (AA) — Eq. 1–2
  2. PUF CRP enrollment — Eq. 3–4
  3. Kyber key establishment — Eq. 5–6
  4. Fog node infrastructure — Eq. 7–8
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from phase1_system_init.attribute_authority import AttributeAuthority
from phase1_system_init.crp_database import CRPDatabase
from phase1_system_init.comm_init import PostQuantumComm
from phase1_system_init.fog_node import FogNode, create_fog_infrastructure
from crypto_primitives.puf import SRAM_PUF
import config


def run_phase1():
    """Execute Phase I and return all initialized components."""
    print("=" * 70)
    print("  PHASE I: System Initialization")
    print("=" * 70)

    # ─── Step 1: Security Initialization ────────────────────────────
    print("\n[Step 1] Security Initialization — CP-ABE Setup")
    aa = AttributeAuthority()
    mpk, msk = aa.setup()
    print(f"  Attribute universe Ω = {aa.attribute_universe}")
    print(f"  MPK keys: {list(mpk.keys())}")

    # Issue keys for two sample authorized users
    sk_engineer = aa.keygen("user_alice", ["Engineer", "Supervisor"])
    sk_operator = aa.keygen("user_bob", ["Operator", "Analyst"])
    print(f"  Issued SK for user_alice: attributes = {list(sk_engineer.keys())}")
    print(f"  Issued SK for user_bob:   attributes = {list(sk_operator.keys())}")

    # ─── Step 1b: PUF CRP Enrollment ───────────────────────────────
    print("\n[Step 1b] PUF CRP Database Enrollment")
    crp_db = CRPDatabase()
    devices_pufs = {}

    for i in range(1, config.NUM_IIOT_DEVICES + 1):
        device_id = f"D_{i}"
        puf = SRAM_PUF(size=config.PUF_RESPONSE_SIZE, ber=config.PUF_BER)
        crp = crp_db.register_device(device_id, puf)
        devices_pufs[device_id] = puf

    print(f"  Enrolled {len(crp_db.registered_devices)} devices")
    print(f"  Sample CRP for D_1: challenge={crp_db.lookup('D_1')['challenge'][:8].hex()}...")

    # Verify authentication for first device
    auth_ok = crp_db.authenticate("D_1", devices_pufs["D_1"])
    print(f"  Authentication test for D_1: {'PASS' if auth_ok else 'FAIL'}")

    # ─── Step 2: Post-Quantum Communication Initialization ─────────
    print("\n[Step 2] Post-Quantum Communication — Kyber Key Establishment")
    pq_comm = PostQuantumComm()

    # Gateway keygen
    gw_pk, gw_sk = pq_comm.keygen_for_entity("GW")
    print(f"  Gateway Kyber PK: {len(gw_pk)} bytes")

    # Fog node keygen
    for i in range(1, config.NUM_FOG_NODES + 1):
        pq_comm.keygen_for_entity(f"F_{i}")
    print(f"  Generated Kyber keys for {config.NUM_FOG_NODES} fog nodes")

    # Establish shared root keys for devices
    device_root_keys = {}
    for device_id in list(devices_pufs.keys())[:5]:  # demo first 5
        ct_kem, k_root = pq_comm.establish_shared_key(device_id, "GW")
        device_root_keys[device_id] = k_root
    print(f"  Established shared root keys for {len(device_root_keys)} devices")
    print(f"  Sample K_root for D_1: {device_root_keys['D_1'][:8].hex()}...")

    # ─── Step 3: Scheduling Infrastructure ─────────────────────────
    print("\n[Step 3] Scheduling Infrastructure — Fog Node Initialization")
    fog_nodes = create_fog_infrastructure(n=config.NUM_FOG_NODES, seed=42)

    print(f"  Created {len(fog_nodes)} fog nodes:")
    for node in fog_nodes:
        state = node.runtime_state
        print(
            f"    {node.node_id}: "
            f"CPU={state['C_j']:.3f}, MEM={state['M_j']:.3f}, "
            f"LAT={state['L_j']:.1f}ms, Q={state['Q_j']:.2f}, "
            f"U={state['U_j']:.2f}"
        )

    print("\n  Phase I Complete ✓")

    return {
        "aa": aa,
        "crp_db": crp_db,
        "pq_comm": pq_comm,
        "fog_nodes": fog_nodes,
        "devices_pufs": devices_pufs,
        "device_root_keys": device_root_keys,
    }


if __name__ == "__main__":
    run_phase1()

"""
Phase II: Hardware-Bound IIoT Protection — Demonstration
=========================================================
Creates IIoT devices, derives hardware-bound keys from PUF secrets
and Kyber root keys, then encrypts sensor data packets.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from phase1_system_init.demo import run_phase1
from phase2_iiot_protection.iiot_device import IIoTDevice
import config


def run_phase2(phase1_ctx=None):
    """Execute Phase II using Phase I context."""
    if phase1_ctx is None:
        phase1_ctx = run_phase1()

    print("\n" + "=" * 70)
    print("  PHASE II: Hardware-Bound IIoT Protection")
    print("=" * 70)

    crp_db = phase1_ctx["crp_db"]
    devices_pufs = phase1_ctx["devices_pufs"]
    device_root_keys = phase1_ctx["device_root_keys"]

    # Create IIoT device instances for devices with root keys
    iiot_devices = {}
    for device_id, puf in devices_pufs.items():
        if device_id not in device_root_keys:
            continue
        crp = crp_db.lookup(device_id)
        if crp is None:
            continue

        device = IIoTDevice(
            device_id=device_id,
            puf=puf,
            challenge=crp["challenge"],
            helper_data=crp["helper_data"],
            k_root=device_root_keys[device_id],
        )
        iiot_devices[device_id] = device

    print(f"\n  Created {len(iiot_devices)} IIoT device instances")

    # Generate protected packets
    all_packets = []
    for device_id, device in iiot_devices.items():
        # Each device generates 3 sensor readings
        for reading in range(3):
            sensor_data = os.urandom(256)
            packet = device.sense_and_protect(sensor_data)
            all_packets.append((device, packet))

    print(f"  Generated {len(all_packets)} protected packets")

    # Show sample packet details
    sample_dev, sample_pkt = all_packets[0]
    print(f"\n  Sample packet from {sample_pkt['device_id']}:")
    print(f"    Counter:   {sample_pkt['counter']}")
    print(f"    CT length: {len(sample_pkt['ct'])} bytes")
    print(f"    Nonce:     {sample_pkt['nonce'].hex()}")
    print(f"    AAD:       {sample_pkt['aad'][:40]}...")

    # Verify decryption roundtrip for sample packet
    from crypto_primitives.chacha20 import SecureChaCha20
    from phase2_iiot_protection.key_derivation import derive_packet_key
    from phase2_iiot_protection.packet_protection import build_aad

    k_p = derive_packet_key(
        sample_dev.k_base,
        sample_pkt["timestamp"],
        sample_pkt["counter"],
    )
    aad = build_aad(
        sample_pkt["device_id"],
        sample_pkt["timestamp"],
        sample_pkt["counter"],
    )
    chacha = SecureChaCha20(key=k_p)
    plaintext = chacha.decrypt(
        sample_pkt["ct"],
        sample_pkt["nonce"],
        associated_data=aad,
    )
    print(f"    Decrypt OK: {len(plaintext)} bytes recovered")

    print("\n  Phase II Complete ✓")

    # Return packets (without device refs, for gateway use)
    return {
        **phase1_ctx,
        "iiot_devices": iiot_devices,
        "packets": [pkt for _, pkt in all_packets],
    }


if __name__ == "__main__":
    run_phase2()

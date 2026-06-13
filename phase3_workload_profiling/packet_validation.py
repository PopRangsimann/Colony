"""
Packet Validation
==================
Verifies AEAD integrity tags and enforces replay protection at the
edge gateway before packets enter the fog infrastructure.

Implements Phase III — Step 1 (Eq. 15–16).

    P_i = {ID, CT, N, Tag, AAD}
    Accept iff Verify(P_i) = 1  AND  no replay detected.
"""

from __future__ import annotations

import sys
import os
from typing import Any, Dict, Optional, Set, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crypto_primitives.chacha20 import SecureChaCha20
from phase2_iiot_protection.key_derivation import derive_base_key, derive_packet_key
from phase2_iiot_protection.packet_protection import build_aad


class ReplayTracker:
    """
    Tracks per-device (timestamp, counter) pairs to detect replays.
    """

    def __init__(self):
        # device_id -> highest counter seen
        self._counters: Dict[str, int] = {}

    def is_replay(self, device_id: str, counter: int) -> bool:
        """
        Returns True if this counter has already been seen or is
        older than the highest recorded counter for this device.
        """
        last = self._counters.get(device_id, 0)
        if counter <= last:
            return True
        self._counters[device_id] = counter
        return False


def validate_packet(
    packet: Dict[str, Any],
    device_keys: Dict[str, bytes],
    replay_tracker: Optional[ReplayTracker] = None,
) -> bool:
    """
    Validate a received packet by checking:
      1. AEAD tag integrity (ChaCha20-Poly1305 decryption succeeds)
      2. Freshness / replay resistance (counter is monotonically increasing)

    Parameters
    ----------
    packet : dict
        Protected packet P_i from Phase II.
    device_keys : dict
        Mapping device_id -> K_base (hardware-bound base key).
        The gateway must have reconstructed K_base for each device
        using its own Kyber decapsulation and PUF CRP data.
    replay_tracker : ReplayTracker, optional
        Replay detection state.

    Returns
    -------
    bool
        True if the packet passes validation.
    """
    device_id = packet.get("device_id")
    if device_id is None or device_id not in device_keys:
        return False

    # Replay check
    if replay_tracker is not None:
        if replay_tracker.is_replay(device_id, packet["counter"]):
            return False

    # Re-derive the packet key to verify AEAD
    k_base = device_keys[device_id]
    k_p = derive_packet_key(k_base, packet["timestamp"], packet["counter"])

    # Reconstruct AAD and verify
    aad = build_aad(device_id, packet["timestamp"], packet["counter"])

    try:
        chacha = SecureChaCha20(key=k_p)
        chacha.decrypt(
            packet["ct"],
            packet["nonce"],
            associated_data=aad,
        )
        return True
    except Exception:
        return False

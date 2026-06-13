"""
Micro-Batch Formation
======================
Groups validated packets into workload batches with batch-level
integrity commitments.

Implements Phase III — Step 2 (Eq. 17–20).

    h_i   = H(ID ‖ CT ‖ Tag)                             (Eq. 19)
    GTag  = H(Sort({h_i}) ‖ t_G)                         (Eq. 18)
    B_k   = (BID, P_valid, GTag, t_G)                    (Eq. 20)
"""

from __future__ import annotations

import hashlib
import sys
import os
import time
import uuid
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _packet_hash(packet: Dict[str, Any]) -> bytes:
    """
    Eq. 19:  h_i = H(ID ‖ CT ‖ Tag)

    Compute the per-packet hash for batch integrity.
    The ciphertext field already contains the tag appended by
    ChaCha20-Poly1305, so we hash device_id + ct directly.
    """
    data = (
        packet["device_id"].encode("utf-8")
        + packet["ct"]
    )
    return hashlib.sha256(data).digest()


def compute_batch_tag(
    packets: List[Dict[str, Any]],
    gateway_timestamp: float,
) -> bytes:
    """
    Eq. 18:  GTag = H(Sort({h_i}) ‖ t_G)

    Compute the batch-level integrity commitment by sorting
    per-packet hashes and hashing them with the gateway timestamp.
    """
    hashes = sorted(_packet_hash(pkt) for pkt in packets)
    combined = b"".join(hashes) + str(gateway_timestamp).encode("utf-8")
    return hashlib.sha256(combined).digest()


def form_micro_batch(
    valid_packets: List[Dict[str, Any]],
    gateway_timestamp: float = None,
) -> Dict[str, Any]:
    """
    Eq. 20:  B_k = (BID, P_valid, GTag, t_G)

    Group validated packets into a workload batch with integrity.

    Parameters
    ----------
    valid_packets : list[dict]
        Packets that passed validation in Step 1.
    gateway_timestamp : float, optional
        Gateway timestamp t_G.  Defaults to current time.

    Returns
    -------
    dict
        Batch B_k with fields: BID, packets, GTag, timestamp,
        and per-packet hashes.
    """
    if gateway_timestamp is None:
        gateway_timestamp = time.time()

    bid = str(uuid.uuid4())[:8]  # short batch ID
    gtag = compute_batch_tag(valid_packets, gateway_timestamp)
    packet_hashes = [_packet_hash(pkt) for pkt in valid_packets]

    return {
        "BID": bid,
        "packets": valid_packets,
        "GTag": gtag,
        "timestamp": gateway_timestamp,
        "packet_hashes": packet_hashes,
        "size": len(valid_packets),
    }

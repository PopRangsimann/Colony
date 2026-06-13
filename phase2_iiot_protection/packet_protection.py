"""
Secure Packet Protection
=========================
Encrypts and authenticates IIoT device packets using
ChaCha20-Poly1305 AEAD with hardware-bound keys.

Implements Phase II — Steps 2–3 (Eq. 12–14).

    AAD_i           = ID ‖ t ‖ ctr                   (Eq. 12)
    (CT_i, Tag_i)   ← AEAD.Enc(K_p, N, m, AAD)      (Eq. 13)
    P_i             = {ID, CT, N, Tag, AAD}           (Eq. 14)
"""

from __future__ import annotations

import sys
import os
from typing import Any, Dict, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crypto_primitives.chacha20 import SecureChaCha20


def build_aad(
    device_id: str,
    timestamp: float,
    counter: int,
) -> bytes:
    """
    Eq. 12:  AAD_i = ID ‖ t ‖ ctr

    Construct the Associated Authenticated Data for a packet.
    """
    return (
        device_id.encode("utf-8")
        + b"|"
        + str(timestamp).encode("utf-8")
        + b"|"
        + counter.to_bytes(8, byteorder="big")
    )


def encrypt_packet(
    k_p: bytes,
    message: bytes,
    aad: bytes,
) -> Tuple[bytes, bytes]:
    """
    Eq. 13:  (CT_i, Tag_i) ← AEAD.Enc(K_p, N, m, AAD)

    Encrypt and authenticate a data packet using ChaCha20-Poly1305.

    Parameters
    ----------
    k_p : bytes
        32-byte packet key.
    message : bytes
        Plaintext sensor data m_i.
    aad : bytes
        Associated authenticated data.

    Returns
    -------
    (ct_and_tag, nonce)
        The ciphertext concatenated with the Poly1305 tag,
        and the 12-byte nonce.
    """
    chacha = SecureChaCha20(key=k_p)
    ct_and_tag, nonce = chacha.encrypt(message, associated_data=aad)
    return ct_and_tag, nonce


def build_packet(
    device_id: str,
    ct_and_tag: bytes,
    nonce: bytes,
    aad: bytes,
    timestamp: float,
    counter: int,
) -> Dict[str, Any]:
    """
    Eq. 14:  P_i = {ID, CT, N, Tag, AAD}

    Assemble the protected packet structure.
    """
    return {
        "device_id": device_id,
        "ct": ct_and_tag,           # ciphertext + Poly1305 tag
        "nonce": nonce,
        "aad": aad,
        "timestamp": timestamp,
        "counter": counter,
    }

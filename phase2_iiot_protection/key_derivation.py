"""
Hardware-Bound Key Derivation
==============================
Derives hardware-bound cryptographic keys for IIoT device packet
protection using PUF secrets and post-quantum shared keys.

Implements Phase II — Steps 1–2 (Eq. 9–11).

    R_secret   ← FuzzyRep(R_noisy, HD)             (Eq. 9)
    K_base     = KDF(K_root ‖ R_secret ‖ ID)       (Eq. 10)
    K_p        = KDF(K_base ‖ t ‖ ctr)              (Eq. 11)
"""

from __future__ import annotations

import hashlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crypto_primitives.puf import FuzzyExtractor


def recover_puf_secret(
    puf,
    challenge: bytes,
    helper_data: bytes,
) -> bytes:
    """
    Eq. 9:  R_secret ← FuzzyRep(R_noisy, HD)

    Re-evaluate the PUF with the stored challenge and recover the
    stable secret using the fuzzy extractor's helper data.

    Parameters
    ----------
    puf : SRAM_PUF
        The device's PUF instance.
    challenge : bytes
        The challenge stored during enrollment.
    helper_data : bytes
        Helper data from the fuzzy extractor enrollment.

    Returns
    -------
    bytes
        Recovered stable PUF secret R_secret.
    """
    noisy_response = puf.evaluate(challenge)
    return FuzzyExtractor.reproduce(noisy_response, helper_data)


def derive_base_key(
    k_root: bytes,
    r_secret: bytes,
    device_id: str,
) -> bytes:
    """
    Eq. 10:  K_base = KDF(K_root ‖ R_secret ‖ ID)

    Derive a hardware-bound root key combining the post-quantum
    shared secret with the PUF-derived secret and device identity.

    Parameters
    ----------
    k_root : bytes
        Post-quantum shared root key from Kyber (Phase I).
    r_secret : bytes
        Stable PUF secret recovered via fuzzy extractor.
    device_id : str
        Device identifier string.

    Returns
    -------
    bytes
        32-byte hardware-bound base key K_base.
    """
    material = k_root + r_secret + device_id.encode("utf-8")
    return hashlib.sha256(material).digest()


def derive_packet_key(
    k_base: bytes,
    timestamp: float,
    counter: int,
) -> bytes:
    """
    Eq. 11:  K_p = KDF(K_base ‖ t ‖ ctr)

    Derive a fresh per-packet encryption key.

    Parameters
    ----------
    k_base : bytes
        Hardware-bound base key from derive_base_key().
    timestamp : float
        Packet timestamp.
    counter : int
        Monotonic packet counter.

    Returns
    -------
    bytes
        32-byte packet key K_p.
    """
    t_bytes = str(timestamp).encode("utf-8")
    ctr_bytes = counter.to_bytes(8, byteorder="big")
    material = k_base + t_bytes + ctr_bytes
    return hashlib.sha256(material).digest()

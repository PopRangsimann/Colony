"""
IIoT Device
============
Resource-constrained sensor/actuator with PUF-based identity.
Generates sensing data and performs lightweight authenticated
encryption before transmission.

Wraps Phase II Steps 1–3 into a single device class that:
  • Recovers the PUF secret (Eq. 9)
  • Derives hardware-bound keys (Eq. 10–11)
  • Encrypts packets with AEAD (Eq. 12–14)
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crypto_primitives.puf import SRAM_PUF
from phase2_iiot_protection.key_derivation import (
    recover_puf_secret,
    derive_base_key,
    derive_packet_key,
)
from phase2_iiot_protection.packet_protection import (
    build_aad,
    encrypt_packet,
    build_packet,
)


class IIoTDevice:
    """
    Represents a single IIoT device with PUF-based hardware identity.

    Parameters
    ----------
    device_id : str
        Unique device identifier.
    puf : SRAM_PUF
        The device's physical unclonable function.
    challenge : bytes
        CRP challenge from enrollment (Phase I).
    helper_data : bytes
        Fuzzy extractor helper data from enrollment.
    k_root : bytes
        Post-quantum shared root key from Kyber (Phase I).
    """

    def __init__(
        self,
        device_id: str,
        puf: SRAM_PUF,
        challenge: bytes,
        helper_data: bytes,
        k_root: bytes,
    ):
        self.device_id = device_id
        self.puf = puf
        self.challenge = challenge
        self.helper_data = helper_data
        self.k_root = k_root
        self.counter: int = 0

        # Derive the hardware-bound base key during initialization
        self.r_secret = recover_puf_secret(puf, challenge, helper_data)
        self.k_base = derive_base_key(k_root, self.r_secret, device_id)

    def sense_and_protect(
        self,
        data: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Simulate sensing data and produce a fully protected packet P_i.

        Parameters
        ----------
        data : bytes, optional
            Raw sensor data.  If None, generates random 256-byte payload.

        Returns
        -------
        dict
            Protected packet P_i = {ID, CT, N, Tag, AAD}.
        """
        if data is None:
            data = os.urandom(256)

        # Timestamp and monotonic counter
        ts = time.time()
        self.counter += 1

        # Eq. 11:  K_p = KDF(K_base ‖ t ‖ ctr)
        k_p = derive_packet_key(self.k_base, ts, self.counter)

        # Eq. 12:  AAD = ID ‖ t ‖ ctr
        aad = build_aad(self.device_id, ts, self.counter)

        # Eq. 13:  (CT, Tag) ← AEAD.Enc(K_p, N, m, AAD)
        ct_and_tag, nonce = encrypt_packet(k_p, data, aad)

        # Eq. 14:  P_i = {ID, CT, N, Tag, AAD}
        return build_packet(
            device_id=self.device_id,
            ct_and_tag=ct_and_tag,
            nonce=nonce,
            aad=aad,
            timestamp=ts,
            counter=self.counter,
        )

    def __repr__(self):
        return f"IIoTDevice({self.device_id}, counter={self.counter})"

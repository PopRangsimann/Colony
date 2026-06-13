"""
Post-Quantum Communication Initialization
==========================================
Establishes CRYSTALS-Kyber key pairs for gateways and fog nodes,
and derives shared root keys between IIoT devices and gateways.

Implements Phase I — Step 2 (Eq. 5–6).

    (pk_x, sk_x)              ← KeyGen_Kyber(1^λ)
    (CT_i^KEM, K_i^root)      ← Encaps(pk_GW)
"""

from __future__ import annotations

import sys
import os
from typing import Dict, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crypto_primitives.kyber import SecureKyber


class PostQuantumComm:
    """
    Manages CRYSTALS-Kyber key pairs and shared key establishment
    for all entities in the fog infrastructure.

    Attributes
    ----------
    entities : dict[str, dict]
        Keyed by entity ID.  Each entry holds 'pk', 'sk', and
        the Kyber instance.
    shared_keys : dict[str, bytes]
        Shared root keys K_i^root, keyed by device_id.
    """

    def __init__(self):
        self.entities: Dict[str, Dict] = {}
        self.shared_keys: Dict[str, bytes] = {}

    # ─── Eq. 5:  (pk_x, sk_x) ← KeyGen_Kyber(1^λ) ────────────────

    def keygen_for_entity(self, entity_id: str) -> Tuple[bytes, bytes]:
        """
        Generate a CRYSTALS-Kyber key pair for the given entity.

        Parameters
        ----------
        entity_id : str
            Identifier of the entity (e.g. "GW", "F_1", ..., "F_n").

        Returns
        -------
        (pk, sk)
            Kyber public key and secret key.
        """
        kyber = SecureKyber()
        pk, sk = kyber.keygen()
        self.entities[entity_id] = {
            "pk": pk,
            "sk": sk,
            "kyber": kyber,
        }
        return pk, sk

    # ─── Eq. 6:  (CT_i^KEM, K_i^root) ← Encaps(pk_GW) ────────────

    def establish_shared_key(
        self,
        device_id: str,
        gateway_id: str = "GW",
    ) -> Tuple[bytes, bytes]:
        """
        Establish a post-quantum shared root key between a device
        and the gateway via Kyber encapsulation.

        Parameters
        ----------
        device_id : str
            IIoT device identifier.
        gateway_id : str
            Gateway entity identifier (default "GW").

        Returns
        -------
        (ct_kem, k_root)
            Kyber ciphertext and the shared root key.
        """
        gw = self.entities.get(gateway_id)
        if gw is None:
            raise ValueError(
                f"Gateway '{gateway_id}' not registered. "
                f"Call keygen_for_entity('{gateway_id}') first."
            )

        kyber = SecureKyber()
        ct_kem, k_root = kyber.encap(gw["pk"])
        self.shared_keys[device_id] = k_root

        return ct_kem, k_root

    def decapsulate(
        self,
        ct_kem: bytes,
        gateway_id: str = "GW",
    ) -> bytes:
        """
        Gateway-side decapsulation to recover the shared root key.

        Returns
        -------
        bytes
            The shared root key K_i^root.
        """
        gw = self.entities[gateway_id]
        kyber = gw["kyber"]
        return kyber.decap(ct_kem, gw["sk"])

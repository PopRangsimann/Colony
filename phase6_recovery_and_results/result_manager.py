"""
Secure Result Management
=========================
Aggregates execution results, generates integrity digests, and
protects results with CP-ABE-based access control before
outsourcing to cloud storage.

Implements Phase VI — Steps 3–4 (Eq. 45–51).

    R_k         = Combine(R_1, ..., R_h)                    (Eq. 45-46)
    H_k         = H(R_k ‖ BID ‖ t_k)                       (Eq. 47)
    K_k         ← {0,1}^λ                                   (Eq. 48)
    CT^ABE_k    = Encrypt(MPK, K_k, P_k)                    (Eq. 49)
    CT_k        = AES-GCM.Enc(K_k, R_k)                     (implied)
    O_k         = (CT_k, CT^ABE_k, H_k)                     (Eq. 51)
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from crypto_primitives.aes_gcm import SecureAESGCM
from crypto_primitives.cp_abe import LatticeCPABE, full_encrypt


class ResultManager:
    """
    Manages result aggregation, protection, and outsourcing.

    Parameters
    ----------
    cpabe : LatticeCPABE
        CP-ABE instance from the Attribute Authority.
    mpk : any
        Master public key.
    """

    def __init__(self, cpabe: LatticeCPABE, mpk):
        self.cpabe = cpabe
        self.mpk = mpk
        self.cloud_storage: Dict[str, Dict] = {}

    def aggregate_results(
        self,
        partial_results: List[Dict[str, Any]],
    ) -> bytes:
        """
        Eq. 45-46:  R_k = Combine(R_1, ..., R_h)

        Reconstruct the final workload result from partial results.
        """
        combined = b""
        for r in partial_results:
            data = r.get("result", b"")
            if isinstance(data, bytes):
                combined += data
        return combined

    def compute_digest(
        self,
        result: bytes,
        batch_id: str,
        timestamp: float = None,
    ) -> bytes:
        """
        Eq. 47:  H_k = H(R_k ‖ BID ‖ t_k)

        Generate a result integrity digest.
        """
        if timestamp is None:
            timestamp = time.time()
        data = (
            result
            + batch_id.encode("utf-8")
            + str(timestamp).encode("utf-8")
        )
        return hashlib.sha256(data).digest()

    def protect_result(
        self,
        result: bytes,
        batch_id: str,
        access_policy: Dict[str, Any] = None,
        timestamp: float = None,
    ) -> Dict[str, Any]:
        """
        Eq. 48-51:  Protect and package the result for outsourcing.

        Steps:
          1. Generate random data key K_k (Eq. 48)
          2. Encrypt K_k under CP-ABE policy (Eq. 49)
          3. Encrypt result with AES-GCM using K_k
          4. Compute integrity digest H_k (Eq. 47)
          5. Package O_k = (CT_k, CT^ABE_k, H_k) (Eq. 51)

        Parameters
        ----------
        result : bytes
            The final workload result R_k.
        batch_id : str
            Batch identifier.
        access_policy : dict, optional
            CP-ABE access policy.  Defaults to config.DEFAULT_ACCESS_POLICY.
        timestamp : float, optional
            Result timestamp.

        Returns
        -------
        dict
            Protected result package O_k.
        """
        if access_policy is None:
            access_policy = config.DEFAULT_ACCESS_POLICY
        if timestamp is None:
            timestamp = time.time()

        # Eq. 48:  K_k ← {0,1}^λ
        k_k = os.urandom(config.RESULT_ENCRYPTION_KEY_BITS // 8)

        # Eq. 49:  CT^ABE_k = Encrypt(MPK, K_k, P_k)
        ct_abe = full_encrypt(self.cpabe, k_k, access_policy)

        # Encrypt result with AES-GCM using K_k
        aes = SecureAESGCM(key=k_k)
        ct_k, iv = aes.encrypt(result)

        # Eq. 47:  H_k = H(R_k ‖ BID ‖ t_k)
        h_k = self.compute_digest(result, batch_id, timestamp)

        # Eq. 51:  O_k = (CT_k, CT^ABE_k, H_k)
        package = {
            "CT_k": ct_k,
            "IV": iv,
            "CT_ABE_k": ct_abe,
            "H_k": h_k,
            "BID": batch_id,
            "timestamp": timestamp,
            "policy": access_policy,
        }

        return package

    def outsource_to_cloud(
        self,
        package: Dict[str, Any],
    ) -> str:
        """
        Store the protected result package in cloud storage.

        Returns the storage key.
        """
        key = package["BID"]
        self.cloud_storage[key] = package
        return key

    def retrieve_from_cloud(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored result package."""
        return self.cloud_storage.get(batch_id)

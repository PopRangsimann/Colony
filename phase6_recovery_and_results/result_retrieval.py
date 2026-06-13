"""
Authorized Result Retrieval
=============================
Enables authorized users to decrypt and verify outsourced results
using their CP-ABE attribute keys.

Implements Phase VI — Step 5 (Eq. 52–55).

    K_k  = Decrypt(SK_u, CT^ABE_k)                          (Eq. 52)
    R_k  = Dec(K_k, CT_k)                                   (Eq. 53)
    H'_k = H(R_k ‖ BID ‖ t_k)                               (Eq. 54)
    Accept iff H'_k = H_k                                    (Eq. 55)
"""

from __future__ import annotations

import hashlib
import sys
import os
from typing import Any, Dict, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crypto_primitives.cp_abe import LatticeCPABE, full_decrypt
from crypto_primitives.aes_gcm import SecureAESGCM


class ResultRetrieval:
    """
    Authorized result retrieval and verification.

    Parameters
    ----------
    cpabe : LatticeCPABE
        CP-ABE instance from the Attribute Authority.
    """

    def __init__(self, cpabe: LatticeCPABE):
        self.cpabe = cpabe

    def recover_data_key(
        self,
        sk_u: Dict,
        ct_abe: Dict[str, Any],
    ) -> Optional[bytes]:
        """
        Eq. 52:  K_k = Decrypt(SK_u, CT^ABE_k)

        Recover the data encryption key using the user's
        attribute secret key.

        Returns None if the user's attributes do not satisfy
        the access policy.
        """
        return full_decrypt(self.cpabe, ct_abe, sk_u)

    def decrypt_result(
        self,
        k_k: bytes,
        ct_k: bytes,
        iv: bytes,
    ) -> bytes:
        """
        Eq. 53:  R_k = Dec(K_k, CT_k)

        Decrypt the result using the recovered data key.
        """
        aes = SecureAESGCM(key=k_k)
        return aes.decrypt(ct_k, iv)

    def verify_integrity(
        self,
        result: bytes,
        batch_id: str,
        timestamp: float,
        expected_hash: bytes,
    ) -> bool:
        """
        Eq. 54-55:  H'_k = H(R_k ‖ BID ‖ t_k);  accept iff H'_k = H_k

        Verify the integrity of the decrypted result.
        """
        data = (
            result
            + batch_id.encode("utf-8")
            + str(timestamp).encode("utf-8")
        )
        h_prime = hashlib.sha256(data).digest()
        return h_prime == expected_hash

    def retrieve_and_verify(
        self,
        package: Dict[str, Any],
        sk_u: Dict,
    ) -> Tuple[Optional[bytes], bool]:
        """
        Full retrieval pipeline:
          1. Recover data key via CP-ABE
          2. Decrypt result via AES-GCM
          3. Verify integrity hash

        Returns
        -------
        (result, integrity_ok)
            The decrypted result (or None) and integrity status.
        """
        # Step 1: Recover K_k
        k_k = self.recover_data_key(sk_u, package["CT_ABE_k"])
        if k_k is None:
            return None, False

        # Step 2: Decrypt result
        try:
            result = self.decrypt_result(k_k, package["CT_k"], package["IV"])
        except Exception:
            return None, False

        # Step 3: Verify integrity
        ok = self.verify_integrity(
            result,
            package["BID"],
            package["timestamp"],
            package["H_k"],
        )

        return result, ok

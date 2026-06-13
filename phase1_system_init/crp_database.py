"""
CRP Database Server
===================
Trusted repository maintaining challenge-response pairs (CRPs) for
registered IIoT devices.  Supports PUF-based device authentication.

Implements Phase I — Step 1: Device CRP Registration (Eq. 3–4).

    R_i    = f_PUF(C_i)
    CRP_i  = (ID_i, C_i, R_i)
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crypto_primitives.puf import SRAM_PUF, FuzzyExtractor
import config


class CRPDatabase:
    """
    Challenge-Response Pair database for PUF-based device enrollment.

    Each registered device stores:
        CRP_i = (device_id, challenge, response, helper_data, stable_secret)

    The helper_data and stable_secret come from the fuzzy extractor's
    enrollment step and are needed later in Phase II for key derivation.
    """

    def __init__(self):
        self._db: Dict[str, Dict[str, Any]] = {}

    # ─── Eq. 3–4:  R_i = f_PUF(C_i);  CRP_i = (ID_i, C_i, R_i) ──

    def register_device(
        self,
        device_id: str,
        puf: SRAM_PUF,
    ) -> Dict[str, Any]:
        """
        Enroll a device by generating a fresh challenge, evaluating the
        PUF, and storing the CRP along with fuzzy-extractor helper data.

        Parameters
        ----------
        device_id : str
            Unique device identifier.
        puf : SRAM_PUF
            The device's PUF instance.

        Returns
        -------
        dict
            The stored CRP record: {id, challenge, response,
            helper_data, stable_secret}.
        """
        # Generate a random challenge
        challenge = os.urandom(32)

        # Eq. 3:  R_i = f_PUF(C_i)
        response = puf.evaluate(challenge)

        # Fuzzy extractor enrollment — produces helper data (public)
        # and the stable secret derived from the enrollment reading.
        stable_secret, helper_data = FuzzyExtractor.generate(response)

        crp = {
            "device_id": device_id,
            "challenge": challenge,
            "response": response,
            "helper_data": helper_data,
            "stable_secret": stable_secret,
        }

        # Eq. 4:  store CRP_i = (ID_i, C_i, R_i)
        self._db[device_id] = crp
        return crp

    def lookup(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the stored CRP for a device.

        Returns None if the device is not registered.
        """
        return self._db.get(device_id)

    def authenticate(self, device_id: str, puf: SRAM_PUF) -> bool:
        """
        Verify a device's identity by re-evaluating the PUF with the
        stored challenge and checking whether the fuzzy extractor
        reproduces the same stable secret.
        """
        crp = self.lookup(device_id)
        if crp is None:
            return False

        # Re-evaluate PUF with stored challenge
        noisy_response = puf.evaluate(crp["challenge"])

        # Reproduce stable secret via fuzzy extractor
        reproduced_secret = FuzzyExtractor.reproduce(
            noisy_response, crp["helper_data"]
        )

        return reproduced_secret == crp["stable_secret"]

    @property
    def registered_devices(self):
        """Return list of registered device IDs."""
        return list(self._db.keys())

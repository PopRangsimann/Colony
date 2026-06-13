"""
Attribute Authority (AA)
========================
Trusted authority responsible for CP-ABE system initialization,
generation of cryptographic parameters, issuance of attribute-based
secret keys, and management of access-control policies.

Implements Phase I — Step 1: Security Initialization (Eq. 1–2).

    (MPK, MSK) ← Setup(1^λ, Ω)
    SK_u       ← KeyGen(MSK, Attr_u)
"""

from __future__ import annotations

import sys
import os
from typing import Any, Dict, List, Optional

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from crypto_primitives.cp_abe import LatticeCPABE
import config


class AttributeAuthority:
    """
    Trusted Attribute Authority for CP-ABE-based access control.

    Attributes
    ----------
    cpabe : LatticeCPABE
        Underlying CP-ABE instance (Waters'11 pairing-based or lattice-based).
    attribute_universe : list[str]
        Set of all recognized attributes Ω.
    mpk : dict
        Master public key.
    msk : dict
        Master secret key.
    user_keys : dict[str, dict]
        Issued attribute secret keys, keyed by user ID.
    """

    def __init__(self, attribute_universe: Optional[List[str]] = None):
        """
        Initialize the Attribute Authority.

        Parameters
        ----------
        attribute_universe : list[str], optional
            Set of valid attributes.  Defaults to config.ATTRIBUTE_UNIVERSE.
        """
        self.attribute_universe = (
            attribute_universe or list(config.ATTRIBUTE_UNIVERSE)
        )
        # The CPABE constructor auto-calls setup(), so mpk/msk are ready
        self.cpabe = LatticeCPABE()
        self.mpk = self.cpabe._mpk
        self.msk = self.cpabe._msk
        self.user_keys: Dict[str, Dict[str, Any]] = {}

    # ─── Eq. 1:  (MPK, MSK) ← Setup(1^λ, Ω) ───────────────────────

    def setup(self) -> tuple:
        """
        Initialize (or re-initialize) the CP-ABE system.

        Returns
        -------
        (mpk, msk)
            Master public key and master secret key.
        """
        self.mpk, self.msk = self.cpabe.setup()
        return self.mpk, self.msk

    # ─── Eq. 2:  SK_u ← KeyGen(MSK, Attr_u) ───────────────────────

    def keygen(self, user_id: str, attributes: List[str]) -> Dict[str, Any]:
        """
        Generate an attribute-bound secret key for user *user_id*.

        Parameters
        ----------
        user_id : str
            Unique identifier for the authorized user.
        attributes : list[str]
            Subset of Ω assigned to this user.

        Returns
        -------
        dict
            Attribute secret key SK_u.

        Raises
        ------
        ValueError
            If any attribute is not in the universe Ω.
        """
        for attr in attributes:
            if attr not in self.attribute_universe:
                raise ValueError(
                    f"Attribute '{attr}' not in universe Ω: "
                    f"{self.attribute_universe}"
                )
        sk_u = self.cpabe.keygen(self.msk, attributes)
        self.user_keys[user_id] = sk_u
        return sk_u

    def get_cpabe(self) -> LatticeCPABE:
        """Return the underlying CP-ABE instance (needed by Phase VI)."""
        return self.cpabe

"""
Autonomous Leadership Recovery
================================
Implements the three-level recovery hierarchy for coordinator
replacement without global re-election.

Recovery Hierarchy:
  Level 1: SMFN takes over as MFN
  Level 2: Cache node with highest RS_j promoted (Eq. 43–44)
  Level 3: Decentralized voting fallback

Implements Phase VI — Step 2 (Eq. 43–44).

    RS_j      = μ₁·Ŝ^coord + μ₂·FRI + μ₃·CF                (Eq. 43)
    MFN^new   = argmax RS_j                                   (Eq. 44)
"""

from __future__ import annotations

import sys
import os
import time
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from phase4_load_balancing.state_replication import compute_recovery_score
from phase4_load_balancing.coordinator_election import elect_coordinators


class LeadershipRecovery:
    """
    Autonomous coordinator recovery manager.

    Implements the three-level recovery hierarchy described in the paper.
    """

    def __init__(self):
        self.recovery_log: List[Dict[str, Any]] = []

    def level1_recovery(
        self,
        smfn,
        fog_nodes: list,
    ) -> Tuple:
        """
        Level 1: SMFN immediately assumes MFN role.

        Used when only MFN has failed.

        Returns
        -------
        (new_mfn, new_smfn)
        """
        # SMFN becomes MFN
        smfn.is_smfn = False
        smfn.is_mfn = True
        new_mfn = smfn

        # Select new SMFN from remaining nodes
        candidates = [
            n for n in fog_nodes
            if n.is_alive and not n.is_mfn
        ]

        if not candidates:
            self._log_recovery("level1", new_mfn.node_id, None)
            return new_mfn, None

        # Pick the one with highest recovery score
        best = max(candidates, key=lambda n: compute_recovery_score(n))
        best.is_smfn = True
        new_smfn = best

        self._log_recovery("level1", new_mfn.node_id, new_smfn.node_id)
        return new_mfn, new_smfn

    def level2_recovery(
        self,
        cache_nodes: list,
        fog_nodes: list,
    ) -> Tuple:
        """
        Level 2: Cache node with highest RS promoted as new MFN.

        Used when both MFN and SMFN have failed.

        Eq. 44:  MFN^new = argmax RS_j

        Returns
        -------
        (new_mfn, new_smfn)
        """
        # Clear old roles
        for node in fog_nodes:
            node.is_mfn = False
            node.is_smfn = False

        # Find eligible cache nodes
        eligible = [
            n for n in cache_nodes
            if n.is_alive and n.cached_snapshot is not None
        ]

        if not eligible:
            # Fall to Level 3
            return self.level3_recovery(fog_nodes)

        # Eq. 44: argmax RS_j
        rs_scores = [(n, compute_recovery_score(n)) for n in eligible]
        rs_scores.sort(key=lambda x: x[1], reverse=True)

        new_mfn = rs_scores[0][0]
        new_mfn.is_mfn = True

        # Select new SMFN
        new_smfn = None
        if len(rs_scores) > 1:
            new_smfn = rs_scores[1][0]
            new_smfn.is_smfn = True

        self._log_recovery(
            "level2",
            new_mfn.node_id,
            new_smfn.node_id if new_smfn else None,
        )
        return new_mfn, new_smfn

    def level3_recovery(
        self,
        fog_nodes: list,
    ) -> Tuple:
        """
        Level 3: Decentralized voting fallback.

        Used when no eligible cache node exists. Falls back to
        the standard coordinator election procedure.

        Returns
        -------
        (new_mfn, new_smfn)
        """
        # Clear all roles
        for node in fog_nodes:
            node.is_mfn = False
            node.is_smfn = False

        alive = [n for n in fog_nodes if n.is_alive]
        if len(alive) < 2:
            if alive:
                alive[0].is_mfn = True
                self._log_recovery("level3", alive[0].node_id, None)
                return alive[0], None
            raise RuntimeError("No alive nodes available for recovery")

        new_mfn, new_smfn, _ = elect_coordinators(fog_nodes)

        self._log_recovery(
            "level3",
            new_mfn.node_id,
            new_smfn.node_id if new_smfn else None,
        )
        return new_mfn, new_smfn

    def recover(
        self,
        mfn_alive: bool,
        smfn_alive: bool,
        mfn,
        smfn,
        cache_nodes: list,
        fog_nodes: list,
    ) -> Tuple:
        """
        Execute the appropriate recovery level based on failure state.

        Returns
        -------
        (new_mfn, new_smfn, recovery_level)
        """
        if mfn_alive and smfn_alive:
            return mfn, smfn, 0  # no recovery needed

        if not mfn_alive and smfn_alive:
            # Level 1: SMFN takes over
            mfn.simulate_failure()
            new_mfn, new_smfn = self.level1_recovery(smfn, fog_nodes)
            return new_mfn, new_smfn, 1

        if mfn_alive and not smfn_alive:
            # Only SMFN failed — elect a new SMFN
            smfn.simulate_failure()
            candidates = [
                n for n in fog_nodes
                if n.is_alive and not n.is_mfn
            ]
            if candidates:
                best = max(candidates, key=lambda n: compute_recovery_score(n))
                best.is_smfn = True
                self._log_recovery("smfn_replace", mfn.node_id, best.node_id)
                return mfn, best, 0
            return mfn, None, 0

        # Both failed
        mfn.simulate_failure()
        smfn.simulate_failure()
        new_mfn, new_smfn = self.level2_recovery(cache_nodes, fog_nodes)
        return new_mfn, new_smfn, 2

    def _log_recovery(self, level: str, new_mfn_id: str, new_smfn_id: Optional[str]):
        self.recovery_log.append({
            "level": level,
            "new_mfn": new_mfn_id,
            "new_smfn": new_smfn_id,
            "timestamp": time.time(),
        })

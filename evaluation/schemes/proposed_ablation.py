"""
Ablation: Proposed Scheme With Single Helper
===============================================
Identical to ProposedScheme but limits request_assistance to at most
1 helper.  This isolates the scheduling contribution from the
multi-helper contribution, allowing reviewers to see how much of
Colony's advantage comes from each mechanism.
"""

from __future__ import annotations

import sys
import os
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import config
from evaluation import sim_config
from evaluation.schemes.proposed import ProposedScheme
from evaluation.environment import SimFogNode, Workload


class ProposedAblationSingleHelper(ProposedScheme):
    """Colony with max_helpers=1 for ablation study."""

    def request_assistance(self, nodes, overloaded, workload) -> List[SimFogNode]:
        # Run the full helper selection, then keep only the top-1
        helpers = super().request_assistance(nodes, overloaded, workload)
        return helpers[:1]

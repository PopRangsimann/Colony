"""
Edge Gateway
==============
Entry point of the fog infrastructure that authenticates incoming
device traffic, filters invalid packets, aggregates validated data
into workload batches, and profiles each batch.

Orchestrates Phase III: validation → batch formation → profiling.
"""

from __future__ import annotations

import sys
import os
import time
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from phase3_workload_profiling.packet_validation import (
    validate_packet,
    ReplayTracker,
)
from phase3_workload_profiling.batch_formation import form_micro_batch
from phase3_workload_profiling.workload_profiler import profile_workload


class EdgeGateway:
    """
    Edge gateway that receives packets from IIoT devices,
    validates them, forms micro-batches, and generates
    scheduling-aware workload profiles.

    Parameters
    ----------
    device_keys : dict[str, bytes]
        Mapping of device_id -> K_base for packet validation.
    """

    def __init__(self, device_keys: Dict[str, bytes]):
        self.device_keys = device_keys
        self.replay_tracker = ReplayTracker()
        self.batch_count: int = 0

    def process_incoming(
        self,
        packets: List[Dict[str, Any]],
        deadline: float = None,
        app_priority: float = 1.0,
    ) -> Optional[Tuple[Dict[str, Any], Dict[str, float]]]:
        """
        Full Phase III pipeline:
          1. Validate each packet (AEAD + replay check)
          2. Form a micro-batch from valid packets
          3. Profile the batch for scheduling

        Parameters
        ----------
        packets : list[dict]
            Raw packets from IIoT devices.
        deadline : float, optional
            Workload deadline (absolute timestamp).
        app_priority : float
            Application-defined priority.

        Returns
        -------
        (batch, profile) or None if no valid packets.
        """
        # Step 1: Packet validation
        valid_packets = []
        invalid_count = 0
        for pkt in packets:
            if validate_packet(pkt, self.device_keys, self.replay_tracker):
                valid_packets.append(pkt)
            else:
                invalid_count += 1

        if not valid_packets:
            return None

        # Step 2: Micro-batch formation
        gateway_ts = time.time()
        batch = form_micro_batch(valid_packets, gateway_ts)
        self.batch_count += 1

        # Step 3: Workload profiling
        wp = profile_workload(batch, deadline=deadline, app_priority=app_priority)

        return batch, wp

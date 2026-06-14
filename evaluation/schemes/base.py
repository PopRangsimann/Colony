"""
Abstract Base Scheme
=====================
Common interface that all schemes must implement.
The simulator treats every scheme identically through this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple

from evaluation.environment import SimFogNode, Workload


class BaseScheme(ABC):
    """
    Abstract base class for scheduling schemes.

    Every scheme must implement these four methods.
    The simulator calls them identically for all schemes.
    """

    @abstractmethod
    def elect_coordinator(
        self, nodes: List[SimFogNode]
    ) -> Tuple[Optional[SimFogNode], Optional[SimFogNode]]:
        """
        Elect MFN and SMFN from available fog nodes.

        Returns
        -------
        (mfn, smfn) or (mfn, None) if only one node available.
        """
        ...

    @abstractmethod
    def schedule_workload(
        self,
        nodes: List[SimFogNode],
        workload: Workload,
        mfn: Optional[SimFogNode] = None,
        smfn: Optional[SimFogNode] = None,
    ) -> Optional[SimFogNode]:
        """
        Assign a workload to a fog node.

        Returns the selected node, or None if scheduling fails.
        """
        ...

    @abstractmethod
    def handle_failure(
        self,
        nodes: List[SimFogNode],
        failed_node: SimFogNode,
        in_flight_tasks: int = 0,
    ) -> float:
        """
        Handle a node failure and return recovery latency in ms.

        Parameters
        ----------
        in_flight_tasks : int
            Number of tasks currently queued across all alive nodes.
        """
        ...

    @abstractmethod
    def request_assistance(
        self,
        nodes: List[SimFogNode],
        overloaded_node: SimFogNode,
        workload: Workload,
    ) -> List[SimFogNode]:
        """
        Request collaborative assistance from helper nodes.

        Returns a list of helper nodes (may be empty).
        """
        ...

    def notify_helper_assist(
        self,
        node_id: str,
        actual_proc_ms: float,
        start_time: float,
    ) -> None:
        """
        Callback: simulator informs the scheme of actual (helper-reduced)
        processing time after assistance.  Default is a no-op; schemes
        that maintain internal backlog tracking can override this.
        """
        pass

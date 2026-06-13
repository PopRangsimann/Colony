"""Phase V: Recovery-Preserving Collaborative Resource Assistance — package exports."""

from .assistance_request import (
    check_assistance_needed,
    compute_resource_deficit,
    generate_request,
)
from .helper_selection import (
    compute_recovery_capability,
    compute_helper_score,
    select_helpers,
)
from .collaborative import (
    compute_assistance_budget,
    partition_workload,
    combine_results,
)

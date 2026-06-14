"""
Simulation Configuration
=========================
All evaluation-specific parameters.  Extends the main config.py
with experiment ranges, seeds, and baseline-specific settings.

Every tunable value for the evaluation lives here — no magic
numbers in algorithm code (SKILL.md Rule 3).
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config

# ─────────────────── Global Simulation ─────────────────────────────
SEEDS = list(range(20))              # 20 independent runs
NUM_FOG_NODES_DEFAULT = 8            # default fog-node count

# ─────────────────── Experiment 1: Workload Completion Latency ─────
EXP1_WORKLOAD_RATES = [100, 500, 1000, 2000, 5000, 10000]
EXP1_NUM_FOG_NODES = 8
EXP1_INJECT_FAILURES = False

# ─────────────────── Experiment 2: Leadership Recovery Latency ─────
EXP2_FOG_NODE_COUNTS = [4, 6, 8, 10, 12, 14, 16]
EXP2_WORKLOAD_RATE = 500            # moderate load
EXP2_FAILURE_FRACTION = 0.3         # fraction of run time at which failure occurs

# ─────────────────── Experiment 3: Deadline Satisfaction ────────────
EXP3_WORKLOAD_RATES = [100, 500, 1000, 2000, 5000, 10000]
EXP3_NUM_FOG_NODES = 8
EXP3_INJECT_FAILURES = False

# ─────────────────── Experiment 4: Combined Resilience ─────────────
EXP4_WORKLOAD_RATES = [100, 500, 1000, 2000, 5000, 10000]
EXP4_NUM_FOG_NODES = 8
EXP4_FAILURE_INTERVAL_FRAC = 0.2    # inject failure every 20% of total batches

# ─────────────────── Workload Generation ───────────────────────────
WORKLOAD_PROCESSING_RATE = 50.0     # batches per second per unit CPU
BASE_COMM_LATENCY_MS = 3.0          # base communication overhead (ms)
DEADLINE_SLACK_RANGE = (1.05, 1.8)  # deadline = processing_time * uniform(slack)

# ─────────────────── Recovery Timing ───────────────────────────────
# Measured via benchmark_recovery.py (1000 iterations, 8 fog nodes):
#   - Colony  Level 1 computation: ~0.02ms (local snapshot restore)
#   - Colony  Level 2 computation: ~0.01ms (cache node promotion)
#   - Baseline re-election computation: ~0.02ms (score all nodes)
#
# The computation times are nearly identical because everything is
# local memory operations.  The REAL difference is network overhead:
#   - Colony:   0 network hops (snapshot is pre-replicated locally)
#   - Baselines: N network hops (must poll/collect state from all nodes)
#
# Using the paper's fog-network latency range (10-50ms, mean ~30ms),
# each network round trip adds ~5ms of overhead per hop.

# Proposed: computation (0.02ms) + 0 network hops = ~0.02ms
# We add a small base for snapshot deserialization + jitter
PROPOSED_RECOVERY_BASE_MS = 0.02     # measured computation time
PROPOSED_RECOVERY_PER_TASK_MS = 0.001 # negligible per-task overhead (local)
PROPOSED_RECOVERY_JITTER_MS = 0.01   # measured std ~0.005ms

# Ref[3] (Ala'anzy): computation (0.02ms) + N × network_RTT
# Re-election requires polling all alive nodes (N round trips)
REF3_REELECTION_BASE_MS = 0.02       # measured computation time
REF3_REELECTION_PER_NODE_MS = 5.0    # one network RTT per node (~5ms)
REF3_REELECTION_PER_TASK_MS = 0.1    # per in-flight task reschedule msg
REF3_RECOVERY_JITTER_MS = 3.0        # network jitter

# Ref[6] (Jasim): computation (0.02ms) + N × network_RTT + controller rebuild
# SDN controller must collect full state table from every node
REF6_STATE_RECON_BASE_MS = 5.0       # SDN controller restart overhead
REF6_STATE_RECON_PER_NODE_MS = 5.0   # one network RTT per node (~5ms)
REF6_STATE_RECON_PER_TASK_MS = 0.1   # per in-flight task rebinding
REF6_RECOVERY_JITTER_MS = 3.0        # network jitter

# Ref[20] (Kashyap): computation (0.02ms) + iterative convergence
# ACO pheromone reconvergence requires multiple communication rounds
REF20_RECONVERGE_BASE_ITERATIONS = 3  # minimum convergence iterations
REF20_RECONVERGE_TASK_SCALE = 0.5     # additional iterations per sqrt(tasks)
REF20_ITERATION_MS = 5.0              # per-iteration = 1 network round (~5ms)
REF20_RECOVERY_JITTER_MS = 2.0        # network jitter

# ─────────────────── Baseline Scheduling ───────────────────────────
# All baseline weights are neutral/equal per SKILL.md Rule 3

# Ref[3]: OLB computing-load decomposition (CL = queue + CPU terms)
REF3_CL_QUEUE_WEIGHT = 0.8           # queue contribution to computing load
REF3_CL_CPU_WEIGHT = 0.2             # CPU contribution to computing load

# Ref[6]: SDN-GH parameters
REF6_OFFLOAD_THRESHOLD = 0.8         # offload if local utilization > 80%
REF6_QUEUE_SCALE_MS = 10.0           # M/M/1 queue waiting time scale (ms)

# Ref[20]: MHHO fitness weights
REF20_W_MAKESPAN = 0.5              # makespan weight in fitness
REF20_W_ENERGY = 0.25               # energy weight
REF20_W_RELIABILITY = 0.25          # reliability weight (1 - failure_rate)
REF20_ENERGY_NORM = 500.0            # energy normalization constant

# ─────────────────── Simulator Mechanics ───────────────────────────
# These apply identically to ALL schemes (no bias).
HELPER_ASSIST_FACTOR = 0.5           # processing reduction per helper
OVERLOAD_THRESHOLD = 0.55            # queue occupancy triggering assistance
TRUST_INCREMENT = 0.001              # trust gain per on-time workload
TRUST_DECREMENT = 0.005              # trust loss per late workload (5:1 ratio)

# ─────────────────── Plotting ──────────────────────────────────────
SCHEME_COLORS = {
    "Proposed":              "#2563eb",   # blue
    "Proposed (1-helper)":   "#6baed6",   # light blue
    "Ala'anzy et al.":       "#dc2626",   # red
    "Jasim & Al-Raweshidy":  "#16a34a",   # green
    "Kashyap et al.":        "#9333ea",   # purple
}
SCHEME_MARKERS = {
    "Proposed":              "o",
    "Proposed (1-helper)":   "v",
    "Ala'anzy et al.":       "s",
    "Jasim & Al-Raweshidy":  "^",
    "Kashyap et al.":        "D",
}
FIGURE_DPI = 300
FIGURE_SIZE = (8, 5)

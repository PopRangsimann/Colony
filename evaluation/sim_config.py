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
# Proposed: instant recovery from replicated state
PROPOSED_RECOVERY_BASE_MS = 5.0     # fixed small overhead

# Ref[3] (Ala'anzy): full re-election — poll all nodes
REF3_REELECTION_PER_NODE_MS = 15.0  # per-node polling overhead

# Ref[6] (Jasim): SDN state reconstruction
REF6_STATE_RECON_BASE_MS = 30.0     # base reconstruction time
REF6_STATE_RECON_PER_NODE_MS = 10.0 # per-node state collection

# Ref[20] (Kashyap): ACO reconvergence
REF20_RECONVERGE_ITERATIONS = 5     # meta-heuristic iterations
REF20_ITERATION_MS = 12.0           # per-iteration convergence time

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

# ─────────────────── Simulator Mechanics ───────────────────────────
# These apply identically to ALL schemes (no bias).
HELPER_ASSIST_FACTOR = 0.5           # processing reduction per helper
OVERLOAD_THRESHOLD = 0.55            # queue occupancy triggering assistance
TRUST_INCREMENT = 0.001              # trust gain per on-time workload
TRUST_DECREMENT = 0.005              # trust loss per late workload (5:1 ratio)

# ─────────────────── Plotting ──────────────────────────────────────
SCHEME_COLORS = {
    "Proposed":              "#2563eb",   # blue
    "Ala'anzy et al.":       "#dc2626",   # red
    "Jasim & Al-Raweshidy":  "#16a34a",   # green
    "Kashyap et al.":        "#9333ea",   # purple
}
SCHEME_MARKERS = {
    "Proposed":              "o",
    "Ala'anzy et al.":       "s",
    "Jasim & Al-Raweshidy":  "^",
    "Kashyap et al.":        "D",
}
FIGURE_DPI = 300
FIGURE_SIZE = (8, 5)

"""
Colony Framework — Central Configuration
==========================================
Every weight, threshold, count, range, and rate lives here.
No tunable value is allowed inline in algorithm code.
All weights default to neutral/equal values that sum to 1
unless cited otherwise from the paper.

Sections mirror the paper's six phases.
"""

# ─────────────────── Security Parameters ───────────────────────────
SECURITY_PARAM = 128                     # λ — security parameter (bits)
ATTRIBUTE_UNIVERSE = [                   # Ω — attribute universe
    "Engineer", "Supervisor", "Admin",
    "Operator", "Analyst", "Maintenance",
    "QualityControl", "Safety",
]

# ─────────────────── Environment ───────────────────────────────────
NUM_FOG_NODES = 8                        # n — number of fog nodes
NUM_IIOT_DEVICES = 20                    # number of virtual IIoT devices
AGGREGATION_WINDOW_MS = 500              # t_window — batch window (ms)
PACKET_SIZE_RANGE = (256, 8192)          # bytes
WORKLOAD_DEADLINE_RANGE = (0.1, 5.0)    # seconds (100 ms to 5 s)

# ─── Fog Node Resource Ranges (for simulation init) ───
CPU_RANGE = (0.3, 1.0)                   # normalized computational capability
MEMORY_RANGE = (0.3, 1.0)               # normalized available memory
LATENCY_RANGE = (5.0, 50.0)             # communication latency (ms)
QUEUE_CAPACITY = 100                     # max queue depth per fog node

# ─────────────────── Phase I: PUF / Kyber ──────────────────────────
PUF_RESPONSE_SIZE = 32                   # bytes
PUF_BER = 0.02                           # bit-error rate for PUF simulator

# ─────────────────── Phase III: Workload Profiling ─────────────────
# Workload intensity weights:  ω_k = α₁·S_k + α₂·V_k + α₃·D_k  (Eq. 21)
INTENSITY_ALPHA_1 = 1.0 / 3             # batch size weight
INTENSITY_ALPHA_2 = 1.0 / 3             # payload volume weight
INTENSITY_ALPHA_3 = 1.0 / 3             # processing complexity weight

# Recovery priority weights:  ρ_k = β₁·δ_k + β₂·ω_k + β₃·P_k  (Eq. 22)
PRIORITY_BETA_1 = 1.0 / 3               # deadline urgency weight
PRIORITY_BETA_2 = 1.0 / 3               # workload intensity weight
PRIORITY_BETA_3 = 1.0 / 3               # application priority weight

# ─────────────────── Phase IV: Coordinator Election ────────────────
# Coordination score:  S^coord_j = α₁·C + α₂·M - α₃·L + α₄·U + α₅·R  (Eq. 24)
COORD_ALPHA_1 = 0.20                     # computational capability
COORD_ALPHA_2 = 0.20                     # available memory
COORD_ALPHA_3 = 0.20                     # communication latency (negative)
COORD_ALPHA_4 = 0.20                     # trust score
COORD_ALPHA_5 = 0.20                     # readiness factor

# Readiness:  R_j = 1 - (β₁·Q̄ + β₂·M̄ + β₃·L̄)  (Eq. 25)
READINESS_BETA_1 = 1.0 / 3              # normalized queue occupancy
READINESS_BETA_2 = 1.0 / 3              # normalized memory usage
READINESS_BETA_3 = 1.0 / 3              # normalized latency

# Stability penalty:  Ŝ = S - γ·ΔS  (Eq. 26)
STABILITY_GAMMA = 0.1                    # penalty for score variance

# Coordinator scheduling penalty: small overhead for MFN/SMFN
# to deprioritize (not exclude) coordinators for workload processing.
COORD_SCHED_PENALTY = 0.05               # additive penalty on sched score

# ─────────────────── Phase IV: Failure Resilience Index ────────────
# FRI_j = θ₁·U + θ₂·R - θ₃·FR  (Eq. 27)
FRI_THETA_1 = 1.0 / 3                   # trust score
FRI_THETA_2 = 1.0 / 3                   # readiness factor
FRI_THETA_3 = 1.0 / 3                   # failure rate (negative)

# ─────────────────── Phase IV: Scheduling ──────────────────────────
# S^sched = w₁·Q + w₂·L - w₃·C - w₄·M - w₅·U - w₆·FRI + w₇·ρ  (Eq. 28)
# Queue-dominant: at high load Q drives even distribution (like Ref[20]'s
# cap-induced randomness but intentional).  At low load, quality factors
# still steer toward reliable, capable nodes.  Sum = 1.0.
SCHED_W1 = 0.50                          # queue occupancy  (dominant)
SCHED_W2 = 0.05                          # communication latency
SCHED_W3 = 0.10                          # computational capability (neg)
SCHED_W4 = 0.05                          # available memory (neg)
SCHED_W5 = 0.12                          # trust score (neg)
SCHED_W6 = 0.10                          # FRI (neg)
SCHED_W7 = 0.08                          # recovery priority

# EMA smoothing:  S̃ = η·S + (1-η)·S_prev  (Eq. 29)
EMA_ETA = 0.8                            # smoothing factor (higher = more responsive)

# ─────────────────── Phase IV: Recovery State ──────────────────────
# RS_j = μ₁·Ŝ^coord + μ₂·FRI + μ₃·CF  (Eq. 32)
RS_MU_1 = 1.0 / 3                       # coordination score
RS_MU_2 = 1.0 / 3                       # failure resilience index
RS_MU_3 = 1.0 / 3                       # cache freshness

NUM_CACHE_NODES = 3                      # nodes receiving state replicas

# ─────────────────── Phase V: Helper Selection ─────────────────────
# RC_i = ψ₁·FRI + ψ₂·RS  (Eq. 36)
RC_PSI_1 = 0.5                           # FRI weight
RC_PSI_2 = 0.5                           # RS weight

# HScore_i = λ₁·A + λ₂·RC - λ₃·L  (Eq. 37)
HSCORE_LAMBDA_1 = 1.0 / 3               # available capacity
HSCORE_LAMBDA_2 = 1.0 / 3               # recovery capability
HSCORE_LAMBDA_3 = 1.0 / 3               # communication latency (neg)

# Recovery-preserving threshold:  RC_i >= τ_R  (Eq. 38)
TAU_R = 0.5                              # recovery capability threshold

# Assistance budget:  AB_i = κ·A_i·FRI_i  (Eq. 39)
KAPPA = 0.8                              # assistance budget scale

# ─────────────────── Phase VI: Failure Detection ───────────────────
# τ_H — heartbeat failure threshold (seconds)  (Eq. 42)
TAU_H = 2.0                              # failure detection threshold (s)
HEARTBEAT_INTERVAL = 0.5                 # heartbeat period (s)

# ─────────────────── Phase VI: Result Protection ───────────────────
RESULT_ENCRYPTION_KEY_BITS = 256         # K_k key length
DEFAULT_ACCESS_POLICY = {                # default CP-ABE policy
    "type": "AND",
    "attributes": ["Engineer", "Supervisor"],
}

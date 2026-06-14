# Evaluation Methodology

## Overview

The evaluation framework is a discrete-event simulator that benchmarks the proposed Colony scheme against three reference schemes under controlled, reproducible conditions. The simulator processes workload arrivals, scheduling decisions, queue execution, helper-assisted processing, failure injections, and leadership recovery — all using simulated time for deterministic results.

Each experiment is executed across **20 independent random seeds**, with results reported as **mean ± standard deviation**. Every scheme receives an identical deep-copied environment per seed, ensuring a fair comparison under the same workload trace, fog node configuration, and failure schedule.

---

## Simulation Environment

### Fog Node Configuration

Each fog node is characterized by three resource attributes, randomly sampled per seed:

| Parameter | Range | Description |
|-----------|-------|-------------|
| CPU | [0.3, 1.0] | Normalized computational capability |
| Memory | [0.3, 1.0] | Normalized available memory |
| Latency | [5, 50] ms | Communication latency |
| Queue Capacity | 100 | Maximum concurrent tasks per node |
| Initial Trust | 1.0 | Trust score (updated dynamically) |

### Workload Generation

Workload batches arrive following an **exponential inter-arrival process** scaled by the total number of batches. Each workload is characterized by:

- **Size**: Uniformly sampled from [0.1, 1.0] (normalized)
- **Priority**: Uniformly sampled from [0.5, 2.0]
- **Deadline**: Computed as *arrival_time + estimated_completion × slack*, where the slack factor is uniformly sampled from [1.05, 1.8]. The estimated completion time is derived from the average node CPU and the node latency range.

This deadline model ensures that deadlines are achievable under moderate load but become increasingly challenging as the system approaches saturation.

### Processing Model

The processing time for a workload of size $S_k$ on a node with CPU capacity $C_j$ is:

$$t_{proc} = \frac{S_k}{C_j \times R}$$

where $R = 50$ batches/second/unit-CPU is the processing rate. Total completion latency includes communication overhead ($L_j + 3$ ms base) and queuing delay.

### Helper Assistance

When a node becomes overloaded (queue occupancy > 55% or estimated completion exceeds the deadline), the scheme may dispatch helper nodes. Each helper reduces the primary node's processing time by a factor of:

$$t'_{proc} = \frac{t_{proc}}{1 + n_h \times 0.5}$$

where $n_h$ is the number of helpers and 0.5 is the per-helper assist factor. This models parallel distributed processing where helpers share the computational load.

### Trust Dynamics

Node trust scores are dynamically updated based on workload outcomes:
- **On-time completion**: trust += 0.001 (capped at 1.0)
- **Deadline miss**: trust -= 0.005 (floored at 0.0)

The 5:1 penalty-to-reward ratio reflects that reliability failures are more costly than individual successes.

### Failure Injection

Coordinator failures target the Master Fog Node (MFN) or Sub-Master Fog Node (SMFN), randomly selected. Failures are injected at regular intervals up to 90% of the total simulation time. Upon failure:

1. The failed node is marked as inactive
2. The scheme's `handle_failure` method is invoked to compute recovery time
3. Scheduling is paused for the duration of recovery
4. New coordinators are re-elected from surviving nodes

---

## Compared Schemes

| Label | Scheme | Description |
|-------|--------|-------------|
| **Ours** | Colony (Proposed) | Stability-aware scheduling with backlog tracking, helper-aware estimation, and snapshot-based recovery |
| **Ref[3]** | Ala'anzy et al. | OLB-based computing-load decomposition with re-election recovery |
| **Ref[6]** | Jasim & Al-Raweshidy | SDN-GH threshold-based offloading with SDN controller state reconstruction |
| **Ref[20]** | Kashyap et al. | MHHO fitness-based scheduling (makespan/energy/reliability) with ACO pheromone reconvergence |

All schemes share the same simulator, environment, metrics, and execution pipeline. Scheme-specific logic is confined to each scheme's implementation of four interface methods: `elect_coordinator`, `schedule_workload`, `request_assistance`, and `handle_failure`.

---

## Experiment 1: Workload Completion Latency (Fig. 2)

### Objective
Evaluate each scheme's ability to minimize average workload completion latency under increasing load.

### Setup
| Parameter | Value |
|-----------|-------|
| Fog Nodes | 8 |
| Workload Batches | 100, 500, 1,000, 2,000, 5,000, 10,000 |
| Failures | None |
| Seeds | 20 |

### Independent Variable
Number of workload batches (x-axis), representing increasing system load from light (100) to extreme saturation (10,000).

### Metric
**Average Completion Latency (ms)**: The mean of *(completion_time − arrival_time)* across all completed workloads.

$$\bar{L} = \frac{1}{N} \sum_{k=1}^{N} (t_{completion,k} - t_{arrival,k})$$

### What It Measures
This experiment isolates raw scheduling efficiency without failure interference. At low load, differences arise from scheduling quality (node selection). At high load, differences arise from load-balancing effectiveness — schemes that distribute workloads more evenly across nodes achieve lower average queue wait times.

---

## Experiment 2: Leadership Recovery Latency (Fig. 3)

### Objective
Evaluate how quickly each scheme restores scheduling functionality after a coordinator failure, and how recovery time scales with network size.

### Setup
| Parameter | Value |
|-----------|-------|
| Fog Nodes | 4, 6, 8, 10, 12, 14, 16 |
| Workload Batches | 500 (moderate load) |
| Failures | Injected at 30% of simulation time |
| Seeds | 20 |

### Independent Variable
Number of fog nodes (x-axis), representing increasing network scale.

### Metric
**Recovery Latency (ms)**: The time between failure detection and restoration of scheduling functionality, as reported by each scheme's `handle_failure` method.

### What It Measures
This experiment evaluates the architectural cost of failure recovery. Colony uses pre-replicated state snapshots (zero network hops), while baseline schemes require network polling of all surviving nodes. The metric reflects both computation time and network overhead. Recovery time directly impacts workload loss — workloads arriving during recovery are dropped.

### Recovery Model Per Scheme
- **Colony**: $t_{recovery} = 0.02\text{ms (computation)} + 0.001 \times n_{tasks} + \text{jitter}$ — snapshot is pre-replicated locally, requiring zero network round trips.
- **Ref[3]**: $t_{recovery} = 0.02 + 5.0 \times n_{nodes} + 0.1 \times n_{tasks} + \text{jitter}$ — re-election requires polling all alive nodes.
- **Ref[6]**: $t_{recovery} = 5.0 + 5.0 \times n_{nodes} + 0.1 \times n_{tasks} + \text{jitter}$ — SDN controller must restart and collect full state from every node.
- **Ref[20]**: $t_{recovery} = (3 + 0.5\sqrt{n_{tasks}}) \times 5.0 + \text{jitter}$ — ACO pheromone tables must reconverge over multiple communication rounds.

---

## Experiment 3: Deadline Satisfaction Under Overload (Fig. 4)

### Objective
Evaluate each scheme's ability to meet workload deadlines as the system transitions from underloaded to saturated conditions.

### Setup
| Parameter | Value |
|-----------|-------|
| Fog Nodes | 8 |
| Workload Batches | 100, 500, 1,000, 2,000, 5,000, 10,000 |
| Failures | None |
| Seeds | 20 |

### Independent Variable
Number of workload batches (x-axis), representing increasing system pressure from comfortable to overloaded.

### Metric
**Deadline Satisfaction Ratio (%)**: The percentage of completed workloads that finish before their assigned deadline.

$$DSR = \frac{|\{k : t_{completion,k} \leq d_k\}|}{|\{k : \text{completed}\}|} \times 100\%$$

### What It Measures
While Experiment 1 measures average latency, this experiment measures **tail performance** — the fraction of workloads that meet their individual time constraints. A scheme may have low average latency but poor deadline satisfaction if some workloads experience extreme delays. This experiment tests each scheme's ability to provide consistent, bounded performance under stress.

---

## Experiment 4: System Resilience Under Combined Failures (Fig. 5)

### Objective
Evaluate system robustness when coordinator failures and workload overload occur simultaneously — the most demanding real-world scenario.

### Setup
| Parameter | Value |
|-----------|-------|
| Fog Nodes | 8 |
| Workload Batches | 100, 500, 1,000, 2,000, 5,000, 10,000 |
| Failures | Injected every 20% of total batches |
| Seeds | 20 |

### Independent Variable
Number of workload batches (x-axis), with coordinator failures injected periodically throughout the simulation.

### Metric
**Workload Completion Ratio (%)**: The percentage of all submitted workloads that are successfully completed (regardless of whether they met their deadline).

$$CR = \frac{|\{k : \text{completed}\}|}{|\{k : \text{submitted}\}|} \times 100\%$$

### What It Measures
This experiment combines load stress with failure disruption. Workloads can fail due to:
1. **No alive nodes** — all nodes have failed
2. **System recovering** — workloads arriving during recovery are dropped
3. **Scheduling failure** — scheme unable to assign a node

The completion ratio reflects the overall system availability. Schemes with faster recovery (Experiment 2) lose fewer workloads during recovery windows, while schemes with better load distribution (Experiment 1) handle the remaining workloads more effectively.

---

## Reproducibility

All experiments are fully reproducible via:

```bash
python3 -m evaluation.run_all
```

Results are saved to:
- **Figures**: `evaluation/results/figures/` (PNG, 300 DPI)
- **Data**: `evaluation/results/data/` (CSV with scheme, x_value, mean, std)

The simulation uses fixed random seeds (0–19) and simulated time (not wall-clock), ensuring identical results across runs and platforms.

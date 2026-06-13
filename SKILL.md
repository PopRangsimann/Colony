---
name: fog-eval-simulation
description: >-
  Build the performance-evaluation section, simulation code, and figures for the
  paper "Stability-Aware Load Balancing with Autonomous Leadership Recovery for
  Resilient Fog-Assisted IIoT Systems." Use this skill whenever the user is
  writing or coding any part of the evaluation: implementing the four experiments
  (workload completion latency, leadership recovery latency, deadline satisfaction
  under overload, system resilience under combined failures), implementing or
  comparing the proposed scheme against the three baselines (Ala'anzy et al.,
  Jasim and Al-Raweshidy, Chen et al.), generating the result graphs, choosing
  scheduling weights or thresholds, or drafting the Experimental Setup and
  per-experiment result paragraphs. Trigger this even when the user only mentions
  "the simulation," "graph7," "config.py," "the baselines," "recovery latency,"
  or "the eval section" without naming the full title, because every such task
  must follow the no-bias and no-hardcoded-results rules defined here.
---

# Fog-Assisted IIoT Evaluation Simulation

This skill produces the evaluation artifacts for a fog-computing scheduling and
recovery paper: a reproducible Python simulation, four experiments, comparison
against three published baselines, the result figures, and the matching prose for
the Performance Evaluation section.

The single most important job of this skill is to keep the evaluation honest.
Simulation papers are rejected when a reviewer can show that the proposed method
"wins" because the numbers were assigned rather than measured. Everything below
exists to guarantee that any advantage the proposed framework shows is produced by
its algorithm, not by the experimenter's hand.

## Non-negotiable principles

Read these before writing any code. If a request conflicts with them, raise it
with the user rather than quietly complying.

### 1. No hardcoded results

A metric must never be written as a function of another scheme's metric or as a
literal that favors any scheme. The following is forbidden in every form:

```python
# FORBIDDEN: the proposed result is assigned, not measured
proposed_latency = baseline_latency * 0.6
results["proposed"] = results["chen"] - 12.0
if scheme == "proposed": deadline_ratio += 0.15
```

Every reported number must be the output of running a scheme's real logic against
the simulated environment and reading a counter or timer that the scheme did not
get to set directly. If you cannot trace a plotted value back to an event in the
simulation, it does not go in the figure.

### 2. One environment, one seed, all schemes

Within a single run, every scheme (proposed and all baselines) must see the exact
same generated workload trace, the same node capacities, the same injected failure
times, and the same network conditions. Generate the environment once per seed,
then replay it independently for each scheme. Differences in the output must come
only from how each scheme reacts, never from a different input.

```python
for seed in config.SEEDS:                 # e.g. 20 seeds
    env = build_environment(config, seed)  # workload + nodes + failures, fixed
    for scheme in SCHEMES:                 # proposed + 3 baselines
        sim = Simulator(env.clone(), scheme, config)
        metrics[scheme][seed] = sim.run()
```

### 3. No magic numbers: everything lives in config

Every weight, threshold, count, range, and rate goes in `config.py`. No tunable
value is allowed to appear inline in the algorithm code. This is the transparency
contract with reviewers: they can read one file and see exactly what was set. See
`assets/config_template.py` for the full parameter set drawn from the paper
(coordination weights, FRI/RS weights, scheduling weights, smoothing factor,
helper-selection weights, recovery thresholds, and environment ranges).

When a weight has no principled value, do not silently pick one that helps the
proposed scheme. Either cite a source, set it to a neutral default (for example
equal weights that sum to one), or expose it as a swept parameter and report
sensitivity.

### 4. Identical metric definitions across schemes

Latency, recovery latency, deadline-satisfaction ratio, and completion ratio are
computed by one shared function each, applied identically to every scheme. A
scheme must not get a more generous definition of "completed" or "on time" than
another. Put the metric functions in a `metrics.py` module that the schemes cannot
override.

### 5. Faithful baselines

The three baselines must implement the actual mechanism described in their papers,
not a weakened stand-in built to lose. See `references/baselines.md` for what each
baseline does and does not do. A baseline that is missing recovery logic is allowed
to perform worse on recovery experiments, because that gap is real and is the
paper's point; it is not allowed to be sabotaged on latency by, say, being given a
deliberately bad queue model that its source paper never had.

### 6. Honest reporting

Average over all seeds and report variability (standard deviation or confidence
interval). If the proposed scheme does not lead on some metric, report it and
discuss why rather than hiding or rescaling it. A genuine partial result is more
publishable and more defensible than a suspiciously perfect sweep.

## Workflow

1. Read `assets/config_template.py` and copy it to the project as `config.py`.
   Confirm with the user which parameter values are fixed by the paper and which
   are open. Fill open ones with neutral or cited values.
2. Read `references/baselines.md` and confirm each baseline's behavior with the
   user before coding it.
3. Build the environment generator (`environment.py`): nodes, workload trace,
   failure-injection schedule, all parameterized from config and seeded.
4. Implement the shared metric functions (`metrics.py`).
5. Implement each scheme behind a common interface (`schemes/`), so the simulator
   treats them identically. The proposed scheme implements the Phase IV scoring,
   FRI, RS, and Phase V helper selection from config weights.
6. Run all schemes across all seeds for each experiment, average, and emit both a
   results table (CSV) and the figure.
7. Draft the prose for that experiment using the measured trend, not a predicted
   one.

## The four experiments

Each experiment defines exactly one independent variable and one primary metric.
Do not change anything else between points on the x-axis. The expected qualitative
trends below describe what the mechanisms predict, but the plotted values must come
from the simulation; never seed the trend by hand.

| # | Independent variable | Primary metric | Mechanism under test |
|---|---|---|---|
| 1 | Workload arrival rate (1e2 to 1e4 batches) | Avg workload completion latency | Stability-aware scheduling + FRI |
| 2 | Number of participating fog nodes | Leadership recovery latency | Replicated state + precomputed RS |
| 3 | Workload arrival rate to saturation | Deadline-satisfaction ratio | Recovery-preserving helper selection |
| 4 | Joint overload + injected coordinator failures | Successful workload-completion ratio | Full framework, all mechanisms together |

For each experiment:

- Vary only the stated independent variable; hold all config parameters fixed.
- Run proposed + three baselines on the same environment per seed.
- Recovery latency in Experiment 2 is measured strictly as the wall-clock or
  simulated time between failure detection and the moment scheduling resumes; the
  detection threshold tau_H is the same for every scheme.
- Failure injection times in Experiments 2 and 4 are drawn from the seed and shared
  across schemes, so no scheme is failed at a kinder moment than another.

## Output format for figures

Match the manuscript's figure list (Fig. 2 latency, Fig. 3 recovery, Fig. 4
deadline, Fig. 5 resilience). Use a config-driven plotting helper so style is
consistent and no per-scheme styling secretly emphasizes the proposed line. Save
each figure and the underlying CSV side by side so a reviewer can recompute the
plot from the raw numbers.

## Output format for prose

When drafting the Performance Evaluation paragraphs, follow the user's established
writing preferences: targeted sentence-level edits, clean LaTeX-compatible prose,
and no em dashes. Describe what the measured curves show and attribute the cause to
the specific mechanism, in the same structure the manuscript already uses (state
how each baseline behaves and why, then state the proposed result and its cause).
Do not assert a numerical improvement that the simulation did not produce.

## Reference files

- `assets/config_template.py`: the complete, commented parameter set from the
  paper, ready to copy as `config.py`. Read this first.
- `references/baselines.md`: faithful behavior specification for the three
  baseline schemes and a pre-submission anti-bias checklist. Read before coding the
  schemes.

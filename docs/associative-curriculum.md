# Associative Curriculum Task Spec

This document pins the first Retention Bench-owned curriculum substrate for
constructive-retention model work. It is the implementation spec for RB-2b and
RB-2c.

## Purpose

`blind_spectrum_monitoring` remains the external-validity task for the CL-Bench
pivot: it proves Retention Bench can add hard process-kill resets and reset-axis
reporting to a real upstream task. It is not the right first developmental task
for tiny constructive models.

The first curriculum substrate is **symbolic associative retention**: a small,
deterministic, exact-scored task that teaches synthetic facts and probes whether
the system can recall them and recombine them after hard resets.

This target is intentionally not a frontier-agent benchmark. A tiny model or a
simple JSON-state SUT should be able to expose the mechanics clearly.

## Task Name

Use the task name `symbolic_associative_retention`.

Retention Bench must provide a local task registration path for this name. CL-
Bench's registry currently discovers only modules under its own
`src/tasks/<name>/task.py`, so RB-2b should add a Retention Bench fallback before
or around `retention_bench._clbench.get_task_class` / `list_tasks`. The
`gain_curve` CLI must be able to resolve:

```bash
python -m retention_bench.gain_curve --task symbolic_associative_retention ...
```

without modifying the checked-out CL-Bench dependency.

## CL-Bench Shape

Implement a single-shot `ContinualLearningTask`.

- One instance produces one `Query`.
- One SUT reply produces one `InstanceOutcome`.
- No intra-instance feedback loop is required.
- No C8 multi-step adapter work is in scope.

The response schema should stay minimal:

```python
class AssociativeAnswer(BaseModel):
    answer: str
```

Normalize answers by `strip().lower()` only. Do not add fuzzy matching, aliases,
or an LLM judge.

## Curriculum

The default run teaches synthetic object attributes and deterministic
composition rules.

Example concepts:

- `norb is red`
- `tave is blue`
- `red objects go to bin-a`
- `blue objects go to bin-b`

Example probes:

- Memorization: `What color is norb?` -> `red`
- Transfer: `Which bin should norb go to?` -> `bin-a`

Use generated nonce symbols and a fixed seed. Do not rely on common-world
knowledge.

## Phases And Components

Every instance outcome must include these metadata fields:

| Field | Meaning |
|---|---|
| `phase` | `train`, `recall`, or `transfer` |
| `component` | `context`, `memorization`, or `transfer` |
| `concept_id` | Stable identifier for the taught object/relation |
| `expected` | Exact normalized answer |
| `exposure_index` | Zero-based training exposure count for this concept |
| `probe_after_exposures` | Number of exposures before this probe |

RB-2 defaults to one-shot mode:

- `exposure_index = 0` on the first train exposure.
- `probe_after_exposures = 1` on recall and transfer probes.

The metadata is still required now so RB-3 can add repeated exposure schedules
without changing the task data model.

## Scoring

Only probe instances should contribute to the curriculum headline.

Train/context instances are present in the run stream because the SUT needs a
place to learn the associations, but their reward should be neutral for the
headline. Implement this by giving train instances `reward = 0.0` and reporting
all curriculum headline metrics over probes explicitly.

The invariant is:

- train/context reward is always `0.0`;
- memorization probe reward is `1.0` on exact match, else `0.0`;
- transfer probe reward is `1.0` on exact match, else `0.0`;
- `TaskResult.metrics` reports probe-only means, not just whole-run mean.

Required metrics:

- `probe_mean_reward`
- `memorization_mean_reward`
- `transfer_mean_reward`
- `num_train_instances`
- `num_probe_instances`

If train instances are included in `instance_outcomes`, `TaskResult.summary`
must make clear that the whole-run CL-Bench score includes them and that
`probe_mean_reward` is the curriculum headline.

Because the default schedule includes unscored train instances, the task's
`r_max` should be the maximum possible **mean per-instance reward over the
default full run**, not `1.0`. For example, if 16 of 32 default instances are
scored probes, `r_max = 0.5`.

## Default Schedule

Use a small deterministic default schedule:

1. Train object attributes.
2. Train attribute-to-bin rules.
3. Probe direct object attributes (`component = memorization`).
4. Probe object-to-bin recombinations (`component = transfer`).

Keep the default run short enough for always-on tests. A reasonable first shape:

- 8 concepts.
- 2 attribute/rule groups.
- 8 memorization probes.
- 8 transfer probes.

Constructor knobs should include:

- `num_concepts: int = 8`
- `seed: int = 0`
- `num_exposures: int = 1`
- `probe_after_exposures: int = 1`

RB-2b may accept the repeated-exposure knobs while only testing the default
one-shot behavior. RB-3 owns non-default repeated-exposure metrics.

## Reference SUT

RB-2c should add a keyless JSON-state SUT, separate from the constructive SUT.

Behavior:

- Parse train prompts and persist learned object attributes and attribute rules
  in the survive-dir.
- On memorization probes, answer from persisted object attributes.
- On transfer probes, combine the persisted object attribute with the persisted
  attribute-to-bin rule.
- Flush state before replying.

Expected band:

- `C` (no reset, no wipe): high probe reward, ideally `1.0`.
- `P` (wipe every boundary): low probe reward because prior instances vanish.
- `R(k)` (hard reset without wipe): close to `C` for the JSON SUT.

The reference SUT exists to prove that the task has a retention band. It is not
evidence that the constructive SUT has solved the task.

## Gain-Curve Smoke

RB-2c should make this command shape work, adjusting paths to the implemented
SUT package:

```bash
python -m retention_bench.gain_curve \
  --task symbolic_associative_retention \
  --sut "python -m associative_memory_sut.clbench_main" \
  --extra-pythonpath suts/associative_memory \
  --reset-every 1 --reset-every 2 --name associative-memory
```

RB-2c implements this as `suts/associative_memory/`. The smoke test asserts:

- the curve is not excluded;
- `ceiling > prior`;
- at least one stateful reset arm has a defined `normalised_gain`.

## Repeated Exposure And RL Door

This task is not an RL benchmark yet. It should nevertheless preserve the data
shape needed for one.

The useful first extension is repeated exposure, not reward-feedback policy
learning:

- repeat train/context instances `N` times;
- probe after a configured exposure count;
- report memorization and transfer by exposure count.

RB-3 owns that extension. A later true RL task can add reward/correction
feedback and retry loops if the repeated-exposure curve is useful.

## Out Of Scope For RB-2

- Natural-language corpora or generated stories.
- Fuzzy scoring or LLM-as-judge scoring.
- Multi-step agentic tasks.
- Training or changing the constructive-retention model.
- Reward-feedback retry loops.

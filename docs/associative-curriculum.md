# Associative Curriculum Task Spec

This document pins the first Retention Bench-owned curriculum substrate for
constructive-retention model work. It is the implementation spec for RB-2b and
RB-2c, **amended by RB-16** (probe-space width + held-out composition split —
see "Width, chance level, and the held-out split" below, which supersedes the
original 8-concept / 2-attribute shape wherever the two disagree).

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
- No multi-step (agentic turn-taking) adapter work is in scope.

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

## Width, chance level, and the held-out split (RB-16)

Two properties of the curriculum are load-bearing for validity, and neither was
true of the original shape.

**1. The probe space must be wide enough that chance is unambiguous.** Until
RB-16 the attribute and bin sets were hard-coded pairs, so *both* probe families
were two-way choices at every schedule size: a SUT that answered `red` to every
RECALL and `bin-a` to every TRANSFER scored 0.5 probe-mean, ≈0.308 run-mean —
colliding exactly with `reset_lossy`'s then-published `R(k=12)`. A coin flip was
indistinguishable from the rung documented as partial retention. The task is now
parametrised by `num_attributes` (default **16**, matching
constructive-retention's `composition_bijection` after CR-9), so chance is
`1/16 = 0.0625` per probe and `0.0357` as a run-mean. `suts/random_guess` is the
measured rung that puts that line on the same axis rather than leaving it to be
inferred.

RB uses **nonce words**, not CR's one-distinct-ASCII-byte-per-symbol alphabet.
CR needs single bytes because its SUTs are tiny char-level models where
multi-char names create tokenization/keying confounds; RB's SUTs are LLMs and
JSON-state programs reading prompts, where words are the natural surface. Only
the *width* is shared between the two repos.

**2. Attributes must be shared, with a held-out subset.** If every object has a
private attribute, the attribute is a pass-through relabeling — there is nothing
for a rule to generalize *over*, and worse, a SUT can synthesize `object -> bin`
bridges at **write** time (constructive-retention's bridging mode does exactly
this), turning every TRANSFER probe into a lookup that passes without any
query-time composition.

So: with `num_attributes = A` and `objects_per_attribute = n >= 2`, the schedule
has `A x n` objects, object `i` carries attribute `i % A`, and **the last `A`
objects are held out** — one per attribute, each with `n - 1` bridged exemplars
among the earlier objects. Held-out objects are held out of *bridging*, not of
teaching: they still receive their `TRAIN object_attribute` instance, so RECALL
stays fair for them. Every `TRAIN object_attribute` prompt carries a
`role: bridge|holdout` line (and the same key in query metadata) so a
write-time-bridging SUT can honour the split.

**Held-out transfer is the composition-generalization headline.** It is the same
quantity constructive-retention reports, deliberately, so the two repos' numbers
read against each other. Note that all of RB's own reference SUTs compose at
query time (they persist `object -> attribute` and `attribute -> bin`
separately), so for them bridged and held-out transfer are identical; the split
only bites for systems that shortcut at write time.

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
| `held_out` | RB-16: `true` iff this object is in the never-bridged held-out set |
| `role` | RB-16: `bridge` or `holdout`; present on `TRAIN object_attribute` instances only |

The initial curriculum defaults to one-shot mode:

- `exposure_index = 0` on the first train exposure.
- `probe_after_exposures = 1` on recall and transfer probes.

The metadata is still required now so a later repeated-exposure extension can add schedules
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

Added by RB-16:

- `transfer_bridged_mean_reward`
- `transfer_heldout_mean_reward` — the composition-generalization headline
- `num_transfer_bridged` / `num_transfer_heldout`
- `chance_level` (`1 / num_attributes`)

If train instances are included in `instance_outcomes`, `TaskResult.summary`
must make clear that the whole-run CL-Bench score includes them and that
`probe_mean_reward` is the curriculum headline.

Because the default schedule includes unscored train instances, the task's
`r_max` should be the maximum possible **mean per-instance reward over the
default full run**, not `1.0`. For example, if 16 of 32 default instances are
scored probes, `r_max = 0.5`. It is computed per concrete schedule in
`build_canonical_run_state()` (RB-13); the class attribute is only a
default-schedule fallback for CL-Bench-side tooling that reads it before an
instance exists.

## Default Schedule

Use a small deterministic default schedule:

1. Train object attributes.
2. Train attribute-to-bin rules.
3. Probe direct object attributes (`component = memorization`).
4. Probe object-to-bin recombinations (`component = transfer`).

Keep the default run short enough for always-on tests. The shipped default
(RB-16) is:

- 16 attributes / 16 bins, 2 objects per attribute → **32 objects**, 16 of them
  held out of bridging.
- 32 object-attribute train instances + 16 rule train instances.
- 32 memorization probes.
- 32 transfer probes (16 bridged, 16 held out).
- **112 instances total, `r_max = 64/112 ≈ 0.571`.**

(The pre-RB-16 shape was 8 objects / 2 attributes → 26 instances,
`r_max = 16/26`. It is still regenerable as
`num_attributes=2, objects_per_attribute=4`, so the numbers published against it
are not orphaned; the only delta is the added `role:` line.)

Constructor knobs:

- `num_attributes: int = 16` (>= 2, <= the nonce attribute vocabulary)
- `objects_per_attribute: int = 2` (>= 2 — one object per attribute is held out
  of bridging, so each attribute needs at least one bridged exemplar too)
- `seed: int = 0`
- `num_exposures: int = 1`
- `probe_after_exposures: int = 1`

`num_concepts` is gone: the object count is *derived* (`num_attributes x
objects_per_attribute`) rather than set independently, because the held-out
split only makes sense when objects-per-attribute is explicit.

RB-2b may accept the repeated-exposure knobs while only testing the default
one-shot behavior. Non-default repeated-exposure metrics belong to that later extension.

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

The repeated-exposure extension owns that. A later true RL task can add reward/correction
feedback and retry loops if the repeated-exposure curve is useful.

## Out Of Scope For The Initial Curriculum

- Natural-language corpora or generated stories.
- Fuzzy scoring or LLM-as-judge scoring.
- Multi-step agentic tasks.
- Training or changing the constructive-retention model.
- Reward-feedback retry loops.

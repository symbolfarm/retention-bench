# constructive (train-and-grow) reference SUT

A worked example of the **train-and/or-grow integration seam** (task B13), the
one continual-learning path none of the other reference SUTs touch: this SUT
learns by **mutating its own weights** as it reads. Conforms to
`docs/sut-interface.md`.

This is an **integration example, not a quality baseline.** Model quality is an
explicit non-goal — gibberish QUIZ answers are expected and fine. The point is
that a weights-mutating, capacity-growing model integrates cleanly with the
harness's process + `DIR` contract, including surviving `RESET`.

## What it does

- **READ** — byte-level encode the chapter text; take a *bounded* number of
  next-token (self-supervised LM) gradient steps on it (`STEPS_PER_READ`, not
  train-to-convergence); on the first READ of the run, **grow** capacity by
  adding one transformer block (`storage-delta > 0`); then **flush a checkpoint
  to `DIR` before writing the READ ack** so it survives a `RESET` that
  immediately follows.
- **QUIZ** — greedy-generate a short answer per question from current weights;
  emit a structured `answers` list.
- **Cold vs. resume** — on spawn, if `DIR/checkpoint.pt` exists, rebuild the
  (possibly grown) architecture from the saved config and `load_state_dict`;
  otherwise cold-init a fresh model.

## Substrate

A tiny *from-scratch* byte-level causal transformer (vocab = 256 bytes + BOS),
CPU-only, offline, deterministic given the seed. No HF downloads, no network.
Defaults (`d_model=64`, `n_heads=4`, `n_layers=2`, `block_size=64`) are small
enough to finish the smoke task in a couple of seconds on CPU.

## Checkpoint format

A single `torch.save` blob at `DIR/checkpoint.pt`:

- `config` — the (possibly grown) `ModelConfig` as a dict, read **first** so a
  fresh process rebuilds the right shape *before* `load_state_dict`. This is
  what makes a variable-size checkpoint round-trip after a growth event.
- `model` — the current model `state_dict`.
- `meta` — `train_steps` / `train_flops` / `growth_count` / `read_count` / `seed`.

Written atomically (temp file + `replace`) and flushed every READ, because
`RESET` is `SIGKILL` with no shutdown hook.

## Growth policy

Deterministic and auditable: grow **once**, when READ #1 completes (add one
transformer block). Guarantees exactly one `storage-delta > 0` event and a
checkpoint whose shape differs from a default model.

## Install

```bash
cd suts/constructive
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -e .
```

In a shared/system Python (e.g. inside the dev container) this may require
`--break-system-packages`. The container image below is the reproducible
packaging path and avoids that workaround entirely.

## Container image (preferred packaging)

Unlike the API SUTs, this one extends a **separate CPU-only torch base**
(`retention-bench/sut-torch-cpu-base`) — torch is heavy and only this SUT
needs it, so it is kept out of the slim shared API base:

```bash
# Build the torch-CPU base once:
docker build -f suts/sut-torch-cpu-base.Dockerfile \
  -t retention-bench/sut-torch-cpu-base:0.1 suts/
# Then this SUT's image:
docker build -t retention-bench/sut-constructive:0.1 suts/constructive/
```

The model is from-scratch and offline (no HF downloads); the checkpoint lands
in the bind-mounted `/dir` and survives RESET. The harness launches a SUT in
its image when the manifest declares an `image` field; that wiring (plus the
smoke tests) lands in task **B4c**. See `docs/sut-interface.md` → "Launch
modes".

## Run standalone (smoke check, outside the harness)

```bash
cd "$(mktemp -d)"   # acts as DIR
printf '%s\n' \
  '{"event_id":"e1","event_type":"READ","stage_input":"<TEXT>\nthe old man had a pale blue eye\n</TEXT>"}' \
  '{"event_id":"e2","event_type":"QUIZ","stage_input":"<QUESTION id=\"q1\">What color is the eye?</QUESTION>"}' \
  | python -m constructive
```

Expected: a READ ack carrying a `notes` self-report, then a QUIZ reply with an
`answers` list (content gibberish). A `checkpoint.pt` is left in the cwd.

## Two entrypoints: book-track vs. CL-Bench

This SUT speaks **two** one-line-JSON contracts from the *same* model code
(`model` / `train` / `checkpoint` / `grow`):

- **`python -m constructive`** — the original **book-track** `READ`/`QUIZ` event
  contract (`docs/sut-interface.md`). Used by the standalone smoke above and the
  book-track harness.
- **`python -m constructive.clbench_main`** — the **Continual Learning Bench**
  contract (`{prompt, response_schema, feedback}` → `{action, resource}`), driven
  through `retention_bench.SubprocessSystem` (task **C3**). There is no separate
  `READ` stage in CL-Bench's single-shot tasks, so each *query* is the learning
  signal: a bounded gradient step is taken on the prompt bytes, capacity grows on
  schedule, and the checkpoint is flushed *before* the reply (surviving the hard
  `RESET`'s `SIGKILL`). The reply `action` is synthesised from the query's
  `response_schema` (a generic JSON-Schema→value walker), with leaf values drawn
  from the model's gibberish generation — **schema-valid** so the runner never
  crashes, **model-derived** so the output reflects the constructed weights.
  Reward quality remains a non-goal; the point is that a constructive system runs
  as a CL-Bench system, persists through the reset, and is accounted for in the
  `compute` channel.

`SubprocessSystem` stays generic — all CL-Bench-specific bridging lives in
`clbench_main.py`. See `tests/test_constructive_clbench.py`.

### Sweeping the reset axis (gain-vs-`k`)

`retention_bench.gain_curve` drives this entrypoint over a sweep of hard-reset
densities and renders the retention/gain curve (the pivot's net-new axis,
task **C4**), reconciled against CL-Bench's own `mean_gain`:

```bash
python -m retention_bench.gain_curve --task blind_spectrum_monitoring \
  --task-kwarg variant=five_ch_wide --task-kwarg num_instances=6 \
  --sut "python -m constructive.clbench_main" \
  --extra-pythonpath suts/constructive --reset-every 1 --reset-every 2
```

Because this SUT's reward is gibberish by construction, its band `C − P` is ~0
and the curve correctly reports `EXCLUDED` — the honest negative result, now on
the axis. See `docs/metrics.md` (*Reset-axis curve*) for the formula and the
reconciliation.

To place resets **on vs off a concept-drift boundary** (task **C10**) use the
`default` 3-stage schedule and `--reset-at` instead of `--reset-every` (drifts at
ordinals 30 and 60):

```bash
python -m retention_bench.gain_curve --task blind_spectrum_monitoring \
  --task-kwarg schedule=default --task-kwarg probe_mode=true \
  --sut "python -m constructive.clbench_main" \
  --extra-pythonpath suts/constructive \
  --reset-at "30,60" --reset-at "35,65" --name constructive-drift
```

The `default` schedule needs the `mixed_grid_lifecycle` frozen corpus (ships with
the cl-benchmark dependency; regenerate/verify via `python -m
retention_bench.bsm_corpus --verify`). See `docs/metrics.md` (*Placing resets on
a concept-drift boundary*).

## Configuration

| Env var | Default | Notes |
|---|---|---|
| `CONSTRUCTIVE_SEED` | `0` | RNG seed for reproducible init. |
| `CONSTRUCTIVE_BLOCK_SIZE` | `64` | Context window (bytes). |
| `CONSTRUCTIVE_D_MODEL` | `64` | Model width. |
| `CONSTRUCTIVE_N_HEADS` | `4` | Attention heads. |
| `CONSTRUCTIVE_N_LAYERS` | `2` | Initial block count (grows after the first instance). |
| `CONSTRUCTIVE_GROW_EVERY` | `0` | CL-Bench entrypoint: also grow every N instances (0 = grow only once, at instance 1). |
| `CONSTRUCTIVE_MAX_LAYERS` | `6` | CL-Bench entrypoint: cap on grown block count (bounds CPU cost). |

`RETENTION_BENCH_DIR` (set by the harness) is honoured as the `DIR` path; the
SUT falls back to its cwd, which the harness sets to `DIR` anyway.

## Manifest

See `sut-manifest.json`: `mode=in-context`, `hardware_tier=open`,
`strict_verbatim=true` (folds text into weights; does not cache verbatim spans),
`resource_appendix.kind=local`.

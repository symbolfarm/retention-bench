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

## Configuration

| Env var | Default | Notes |
|---|---|---|
| `CONSTRUCTIVE_SEED` | `0` | RNG seed for reproducible init. |
| `CONSTRUCTIVE_BLOCK_SIZE` | `64` | Context window (bytes). |
| `CONSTRUCTIVE_D_MODEL` | `64` | Model width. |
| `CONSTRUCTIVE_N_HEADS` | `4` | Attention heads. |
| `CONSTRUCTIVE_N_LAYERS` | `2` | Initial block count (grows to 3 after READ #1). |

`RETENTION_BENCH_DIR` (set by the harness) is honoured as the `DIR` path; the
SUT falls back to its cwd, which the harness sets to `DIR` anyway.

## Manifest

See `sut-manifest.json`: `mode=in-context`, `hardware_tier=open`,
`strict_verbatim=true` (folds text into weights; does not cache verbatim spans),
`resource_appendix.kind=local`.

# Debrief: B13 Constructive (train-and-grow) reference SUT

**Completed:** 2026-05-27
**Commit:** 85fedb6

## What shipped

New package `suts/constructive/` — the first reference SUT that learns by
mutating its own weights as it reads:

- Tiny from-scratch byte-level causal transformer (`model.py`), CPU-only,
  offline, deterministic given the seed. Vocab = 256 bytes + BOS.
- `checkpoint.py` — atomic `torch.save` blob at `DIR/checkpoint.pt` carrying
  `{config, model, meta}`; cold-init vs. resume; rebuilds the grown shape from
  the saved config before `load_state_dict`.
- `train.py` — bounded next-token LM training (8 steps/READ, not
  train-to-convergence) + a `lm_loss` helper used by tests to demonstrate
  retention.
- `__main__.py` — the event loop: READ trains, grows once after READ #1,
  **flushes the checkpoint before writing the ack**; QUIZ greedy-generates
  per-question answers; self-reports `param_count`/`train_steps`/`train_flops`/
  `growth_count` via the `notes` field.
- `sut-manifest.json` (`mode=in-context`, `hardware_tier=open`,
  `strict_verbatim=true`, `resource_appendix.kind=local`,
  `entrypoint=["python","-m","constructive"]`), `pyproject.toml` (CPU torch),
  `README.md`.
- Tests: `tests/test_constructive_unit.py` (fast offline:
  train→grow→checkpoint→RESET→reload→answer on a tiny config) +
  `tests/test_constructive_integration.py` (harness drives the real SUT through
  the two_chapter fixture incl. RESET; asserts the grown checkpoint round-trips).
- `docs/sut-interface.md`: refreshed the reference-impl bullets (notes_llm,
  naive_rag, constructive now listed) and added a paragraph that a
  weights-mutating SUT is a valid `in-context` SUT.

Verified end-to-end: full test suite green (1 pre-existing skip — the live
no_state API test). Smoke run `python -m harness tasks/smoke-test/task.yaml
--sut suts/constructive` finished in ~2.3s, produced a trace + checkpoint +
RESET snapshot, and the exact-match scorer rendered a retention curve
(near-zero, as expected for gibberish answers — quality is a non-goal).

## Descoped / deferred

Per the brief: model quality / good retention (non-goal), GPU + hardware-tier
enforcement (B4), container packaging (B4), first-class harness resource fields
for train-FLOPs/storage-delta (`notes` suffices), `strict_verbatim` audit rework.
Nothing additional descoped.

## Design decisions

- **Steered choices (made as suggested in the brief):**
  - *Growth trigger:* deterministic — grow exactly once, when READ #1 completes
    (add one transformer block, `n_layers` 2→3). Simplest auditable policy that
    guarantees one `storage-delta > 0` event and a variable-size checkpoint.
  - *Checkpoint format/cadence:* single atomic `torch.save` blob flushed every
    READ before the ack; config serialised alongside weights so a fresh process
    rebuilds the grown shape before `load_state_dict`.
  - *Tokenizer:* byte-level (256 + BOS), no deps.
  - *Sizing:* defaults `d_model=64`, `n_heads=4`, `n_layers=2`, `block_size=64`
    — smoke run completes in seconds, far inside the 300s/event timeout.
- **torch dependency lives in the SUT's own `suts/constructive/pyproject.toml`,
  not the repo-root `pyproject.toml`.** Followed the existing per-SUT convention
  (no_state/naive_rag each pin their deps in their own pyproject) rather than
  adding a torch extra to the root. The brief's `Touches` named `pyproject.toml`
  generically; I read it as "a pyproject", and the per-SUT one is the
  consistent home. Root pyproject left untouched.
- **Growth preserves learned weights** by copying matching-shape tensors into a
  freshly-built grown model; the new (final) block is randomly initialised.
  Quality is a non-goal, so no attempt at identity-init of the new block.
- **`weights_only=False` on `torch.load`** — the blob holds plain dicts
  (config/meta) beside tensors, and the source is the SUT's own prior-session
  `DIR`, not untrusted input. Noted in `checkpoint.py`.
- **Manifest declares `gpu_model: null`** under the `local` resource appendix,
  since the SUT is CPU-only by design.

## Observations

- The SUT's cwd *is* `DIR` (harness sets it), and `RETENTION_BENCH_DIR` echoes
  it. naive_rag uses `Path.cwd()`; I honour `RETENTION_BENCH_DIR` first then
  fall back to cwd — belt and braces, same effective path.
- The smoke task has only one READ, so exactly one growth event fires and
  `read_count` ends at 1 — confirmed in the run's final checkpoint
  (`n_layers=3`, `growth_count=1`). The post-RESET QUIZ loaded the grown
  checkpoint correctly, which is the whole point of the task.
- No harness change was needed — the local weights-mutating SUT ran cleanly on
  the existing subprocess path, which (as the brief predicted) is useful
  evidence that B4's container contract should generalise beyond API SUTs.
- The unit test pins the load-bearing invariant precisely: weights round-trip
  exactly (LM loss reproduces to 1e-6) when no growth happens between save and
  load; a grown checkpoint reloads with the grown shape + grown param count.

## Follow-ups

### Considered and dropped

- *Add a constructive-SUT row to any leaderboard fixture / README table* — no
  such consolidated table exists yet to update, and the docs note already
  covers the conceptual point. Not worth a task.
- *Make `STEPS_PER_READ` / growth policy harness- or task-configurable* — this
  is explicitly a fork-it-elsewhere integration example; env vars already cover
  sizing. Adding knobs would be gold-plating.

# B13 Constructive (train-and-grow) reference SUT — integration example

**Priority:** medium
**Blocked by:** nothing (runs on the existing `subprocess.Popen(entrypoint)`
launch path; explicitly *not* blocked on B4 — see Decisions)
**Touches:** `suts/constructive/*` (new package), `pyproject.toml` (CPU
torch / deps), `tests/test_constructive_*.py` (new),
`docs/sut-interface.md` (add reference-impl bullet + a short note that a
weights-mutating SUT is a valid `in-context` SUT). No harness change
expected.

## Context

CL-eval is the North Star for the constructive-transformer research: it
defines success as *retention across resets*, not in-distribution loss.
For the harness to actually exert that pull, it needs at least one SUT
that learns by **mutating its own weights as it reads** — the continual-
learning path that none of the three current reference SUTs (`no_state`,
`notes_llm`, `naive_rag`) touch. They are all frozen-model, API-tier,
in-context/RAG rows.

This task is **a worked example of the train-and/or-grow integration
seam**, not a quality baseline. Toby will fork it and develop the real
constructive transformer elsewhere. Model quality is an explicit
non-goal: success is that a model which trains *and grows* on READ
survives RESET via a `DIR` checkpoint and answers QUIZ end-to-end
through the existing process contract.

The hard bit is **checkpoint-across-RESET**: RESET is `SIGKILL` (no
shutdown hook), so any weight update / growth must be flushed to `DIR`
*before* the response to the event that precedes the RESET is written.
This is where the contract actually bites a weights-mutating SUT.

Scoped jointly with Toby on 2026-05-27. See Decisions for what was
settled (and what was deliberately deferred).

## Goal

A reference SUT under `suts/constructive/` that, on each READ, takes a
real gradient step on the READ text (self-supervised next-token LM
loss) and periodically **grows capacity** (storage-delta > 0); persists
a checkpoint to `DIR` that survives RESET; and answers QUIZ by
generating from current weights — demonstrating end-to-end how a
train-and-grow model integrates with the harness.

## Acceptance criteria

- [ ] New package `suts/constructive/` with `sut-manifest.json`
      (`mode: in-context`, `hardware_tier: open`, `strict_verbatim: true`,
      `resource_appendix.kind: "local"`, `entrypoint:
      ["python","-m","constructive"]`).
- [ ] **Train on READ:** each READ performs a real gradient update on
      the READ text (LM loss), then **flushes an updated checkpoint to
      `DIR` before writing the READ ack** (so it survives a RESET that
      immediately follows).
- [ ] **Grow:** at least one growth event over a session adds capacity
      (e.g. an adapter block / widened layer / grown embedding),
      producing `storage-delta > 0` and a **variable-size checkpoint**
      that reloads correctly in a later session.
- [ ] **Survives RESET:** after SIGKILL + respawn, the new process
      reloads the checkpoint and continues — verified by a test that a
      post-RESET state reflects pre-RESET reading (e.g. lower LM loss on
      seen text, or carried-over param count), not from-scratch.
- [ ] **Answer QUIZ:** answers by generating from current weights;
      well-formed `answers` list with matching ids. Content quality is
      a non-goal (gibberish is acceptable).
- [ ] **CPU-only, offline:** no GPU, no network during train/inference;
      deps pinned in `pyproject.toml`; runs inside the dev container and
      finishes the smoke task within the 300s/event timeout.
- [ ] Self-reports `param_count` / `train_steps` / approx `train_flops`
      via the existing free-form `notes` response field (no harness
      change).
- [ ] Drives end-to-end through the harness on the smoke task and
      produces a trace + retention curve like the other SUTs.
- [ ] Fast offline test exercising train → grow → checkpoint → RESET →
      reload → answer on a tiny config.
- [ ] All existing tests still pass.

## Relevant files

- `suts/no_state/`, `suts/naive_rag/` — package layout, manifest,
  `__main__` event-loop, and `pyproject.toml` templates to copy.
- `docs/sut-interface.md` — the contract; add the reference-impl bullet
  and the "weights-mutating SUT is still `in-context`" note.
- `harness/event_loop.py`, `harness/sut_process.py` — read to confirm
  RESET = SIGKILL + respawn-in-same-`DIR` and the checkpoint-flush
  timing; no edits expected.
- `tasks/smoke-test/task.yaml` — the task the end-to-end run uses.

## Decisions already made (2026-05-27 scoping session)

- **Plan A: train + trivial growth** (not train-only, not grow-only).
  The construction path — `storage-delta > 0`, variable-size
  checkpoint — is the one behaviour no other SUT will ever exercise, so
  it earns its place in the template even though it costs a bit more
  than train-only.
- **Integration example, not a baseline.** Model quality is a non-goal;
  Toby forks this for the real constructive transformer elsewhere.
- **`mode: in-context` is correct.** The `agentic | in-context` enum is
  about *how files reach the model* (own scaffold vs. handed in
  context), not whether training happens. A weights-mutating SUT raises
  no leaderboard/contract problem.
- **Resource accounting deferred, not blocking.** Report
  params/steps/FLOPs via the free-form `notes` field for now;
  first-class harness fields for train-FLOPs/storage-delta would be a
  separate small follow-up. (B7 specs the storage-delta=0 in-place rule;
  B11 is judge-side accounting — neither covers SUT-side train capture.)
- **`strict_verbatim` audit revisit deferred.** SUT declares
  `strict_verbatim: true` honestly (it folds text into weights, doesn't
  cache verbatim spans). The audit-mechanism rationale is a separate
  conversation.
- **CPU / `open` tier; GPU has no value here.** A toy model doesn't
  meaningfully exercise a GPU; GPU + hardware-tier *enforcement* is
  B4's concern.
- **Not blocked on B4; landing it first improves B4.** Runs on the
  existing subprocess path. As a fourth, structurally different SUT
  (local weights, torch, checkpoint-in-`DIR`) it makes B4's container
  contract generalise better than three near-identical API SUTs would.
  Interim dep install follows the other SUTs' pattern (per-SUT venv /
  `--break-system-packages`); B4 retires that.
- **Substrate (recommended, implementer may swap):** a tiny
  *from-scratch* byte/char-level transformer to stay offline,
  deterministic, and dependency-light — rather than downloading an HF
  model. Whatever is chosen must stay CPU-only and offline.
- **Training signal:** next-token LM loss on the READ text. QUIZ
  answered by greedy/sampled generation.
- **Name:** `suts/constructive/` (package `constructive`). Veto-able.

## Open questions for the implementer (steered)

1. **Growth-trigger policy.** Every READ? Every N READs? A
   size/loss threshold? Suggest a simple, deterministic, auditable
   policy (e.g. "grow once after READ #1" or "every N READs").
2. **Checkpoint format + cadence.** Flush every READ (RESET can come at
   any time). `torch.save` of the whole model is fine; keep it simple
   and reload-robust across a changed architecture (growth means the
   reloaded shape differs).
3. **Tokenizer.** Byte-level to avoid dependencies.
4. **Sizing.** Defaults small enough that a smoke run completes well
   inside the 300s/event timeout on CPU.

## Out of scope

- Model quality / genuinely-good retention (non-goal).
- GPU execution and hardware-tier *enforcement* (B4).
- Container packaging (B4) — runs on the subprocess path.
- First-class harness resource fields for train-FLOPs / storage-delta
  (possible small follow-up; `notes` suffices here).
- `strict_verbatim` audit-mechanism rework.
- Being the "real" constructive transformer — Toby develops that
  elsewhere; this only demonstrates the integration seam.

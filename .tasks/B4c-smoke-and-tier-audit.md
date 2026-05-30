# B4c Container smoke paths + tier-metadata audit flow + QUICKSTART

**Priority:** medium
**Blocked by:** B4a, B4b (need both the launch engine and the images
before either smoke path can run end-to-end)
**Touches:** `run.sh`, `docs/QUICKSTART.md` (new), `harness/event_loop.py`
(tier-metadata into run-manifest), `harness/sut_process.py` (declared-vs-
actual capability capture), `tests/test_*_fake_anthropic.py` (container
path), `docs/decisions-checklist.md` (tier-declaration resolution)

## Context

Split from B4 (see `.tasks/debriefs/B4.md`). B4a built the launch
engine, B4b built the images; this task proves the whole thing works
end-to-end from both entry points and lands the audit-trail half of
decision #16 (hardware-tier metadata flowing into the run manifest).

## Goal

`./run.sh smoke` works end-to-end both from a bare host (Docker only,
no Python venv) and from inside the dev container (DooD). The SUT's
declared `hardware_tier` and what the host actually exposed both land
in `run-manifest.json` for audit. `docs/QUICKSTART.md` documents the
bare-host path.

## Acceptance criteria

- [ ] **Bare-host smoke test:** `./run.sh smoke` works on a host with
      only Docker installed — no Python venv on the host, no dev
      container. Verified end-to-end at least once and documented in
      `docs/QUICKSTART.md`.
- [ ] **Dev-container smoke test:** `./run.sh smoke` works from inside
      this dev container with DooD (host docker.sock mounted). No
      regression vs. today's run. `HOST_WORKSPACE` translation (defined
      in B4a) exercised here.
- [ ] Hardware-tier metadata flows from `sut-manifest.json` into
      `run-manifest.json`: **both** what the SUT declared and what the
      host actually exposed (e.g. visible GPUs / `nvidia-smi` presence)
      recorded. **Soft enforcement** — record both, don't refuse to run
      on mismatch.
- [ ] `docs/decisions-checklist.md` #16 updated to reflect that
      tier-declaration is now recorded-and-auditable (soft), not just
      trust-only.
- [ ] **Container-path integration coverage.** The option-B shim mount
      (built in B4a) is exercised: at least one fake-anthropic
      integration test drives a SUT *through a container* (`-v
      shim:/shim:ro`), closing the gap B10 opened on the container path.
- [ ] Decide and document whether container spin-up time is folded into
      `wall_clock_ms` or recorded as separate container-overhead. (Lean:
      record overhead separately so retention curves stay comparable to
      the pre-container subprocess runs.)
- [ ] All existing tests still pass.

## Relevant files

- `run.sh` — the `smoke` entry point; may need a bare-host vs.
  dev-container branch or auto-detect.
- `docs/QUICKSTART.md` — new file, bare-host instructions.
- `harness/event_loop.py`, `harness/sut_process.py` — capability capture
  + run-manifest fields.
- `docs/decisions-checklist.md` — #16 resolution.
- `tests/test_no_state_fake_anthropic.py` and siblings — add a
  container-path variant.

## Decisions already made

(From the 2026-05-30 B4-refinement conversation; full context in
`.tasks/debriefs/B4.md`.)

- **Bare-host is a hard requirement**, with its own smoke path — not a
  nice-to-have. The benchmark must be runnable by anyone with Docker.
- **Soft tier enforcement** — record declared vs. actual, let auditors
  compare; don't hard-refuse on mismatch.
- **Bind mounts + `HOST_WORKSPACE`** path translation (defined in B4a);
  this task exercises it on the dev-container smoke path.

## Out of scope

- Harness launch/reset engine — **B4a** (done before this starts).
- The Dockerfiles — **B4b** (done before this starts).
- Registry push / CI image publication, image signing — deferred
  (parent B4).
- Multi-host scheduling, k8s/compose — deferred (parent B4).

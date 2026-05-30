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

### Inherited from B4b (2026-05-30)

B4b deliberately did **not** add the `image` field to the manifests.
Reason: B4a's harness routes to `docker run` on the mere presence of
`image` (`event_loop._make_container_spec`), with no opt-out — so adding
`image` turns the always-on fake-anthropic integration tests red in any
daemonless environment (`FileNotFoundError: docker`). The fix (the
force-subprocess opt-out) lives in this task's scope, so the `image`
additions were moved here to land atomically with it. B4b also could not
run `docker build` (no daemon), so image-build verification is inherited
here too. See `.tasks/debriefs/B4b.md`.

## Goal

`./run.sh smoke` works end-to-end both from a bare host (Docker only,
no Python venv) and from inside the dev container (DooD). The SUT's
declared `hardware_tier` and what the host actually exposed both land
in `run-manifest.json` for audit. `docs/QUICKSTART.md` documents the
bare-host path.

## Acceptance criteria

- [ ] **Add the `image` field to all four `sut-manifest.json` files**
      (`no_state`, `notes_llm`, `naive_rag`, `constructive`), pointing at
      the tags B4b's Dockerfiles produce (`retention-bench/sut-*:0.1`).
      *Moved here from B4b* — see "Inherited from B4b" below; in B4b it
      would have reddened the suite.
- [ ] **Harness force-subprocess opt-out.** Adding `image` routes the
      always-on fake-anthropic integration tests onto the docker path,
      which fails with no daemon. Add a mechanism so those tests keep
      running on the subprocess path (e.g. a `RETENTION_BENCH_FORCE_SUBPROCESS`
      env var honoured in `event_loop._make_container_spec`, or point the
      existing tests at a no-`image` launch). Required for "all existing
      tests still pass" once `image` is declared.
- [ ] **Bare-host smoke test:** `./run.sh smoke` works on a host with
      only Docker installed — no Python venv on the host, no dev
      container. Verified end-to-end at least once and documented in
      `docs/QUICKSTART.md`.
- [ ] **Verify the B4b images actually build** (`docker build` for both
      bases + all four SUT images) — B4b could not, lacking a daemon.
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

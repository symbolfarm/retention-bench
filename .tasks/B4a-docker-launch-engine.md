# B4a Harness docker-run launch engine + manifest contract

**Priority:** medium
**Blocked by:** nothing
**Touches:** `harness/sut_process.py`, `harness/event_loop.py`,
`suts/*/sut-manifest.json`, `docs/sut-interface.md`

## Context

Split from B4 (see `.tasks/debriefs/B4.md` for the split rationale and
the full decision history). B4 was packaging + tier scaffolding + dev-env
cleanup in one task; it was oversized for a single session, so it was
split into B4a (this — the launch *engine*), B4b (the Dockerfiles), and
B4c (smoke paths, QUICKSTART, tier-metadata audit flow).

Per decision #16, SUTs ship as Docker images and the harness launches
them via `docker run` instead of a bare `subprocess.Popen`. This task is
the engine: teach the harness to spawn and reset a containerised SUT
over the identical JSONL stdin/stdout wire contract it uses today. The
Dockerfiles themselves (B4b) and the end-to-end smoke validation (B4c)
come after; B4a is validated against an already-published public image
(e.g. `python:3.11-slim` running a trivial inline echo) plus the
existing tests, so it doesn't block on B4b.

## Goal

The harness can launch a SUT by `docker run -i --rm` against a declared
image, pipe JSONL events over stdin/stdout exactly as today, mount `DIR`
(and the test shim) into the container, and respawn a fresh container on
`RESET` — mirroring today's subprocess lifecycle.

## Acceptance criteria

- [ ] `sut-manifest.json` gains an `image` field. Existing `entrypoint`
      is reinterpreted as the in-container argv. A manifest with an
      `image` launches via docker; a manifest without one keeps the
      current bare-subprocess path (so non-container tests/dev still work).
- [ ] `harness/sut_process.py` `spawn_sut` grows a container-launch path:
      `docker run -i --rm -v <DIR-mount> [-v <shim-mount>] -e <declared
      env> <image> <entrypoint argv>`, stdin/stdout piped identically to
      the `Popen` path.
- [ ] **Generic env passthrough.** The manifest declares which env vars
      the harness forwards into the container (e.g. an `env_passthrough`
      list). The harness does NOT hardcode `ANTHROPIC_API_KEY` /
      `<SUT>_MODEL`. This keeps B9 (provider-neutral backend) a
      manifest-only change later — no harness edit. Names are read from
      the harness's own environment and forwarded with `-e NAME` (value
      passthrough), never logged.
- [ ] `DIR` is bind-mounted into the container at a fixed in-container
      path. Path-translation for the DooD case handled per the decision
      below (`HOST_WORKSPACE`).
- [ ] **Option-B test-shim mount.** When a test sets the shim env, the
      harness adds `-v <shim>:/shim:ro -e PYTHONPATH=/shim`. Production
      launches add neither. One shim source of truth; no `Dockerfile.test`.
- [ ] `RESET` kills the running container and spawns a fresh one (today's
      subprocess-respawn semantics, container edition). The
      PYTHONPATH-on-respawn regression that M7 surfaced must stay fixed
      on the container path too.
- [ ] `docs/sut-interface.md` Invocation section updated to describe the
      `docker run`-based launch, the `image`/`env_passthrough` manifest
      fields, and the no-`image` fallback.
- [ ] All existing tests pass. The fake-anthropic integration tests keep
      working on the no-`image` (bare subprocess) path; exercising them
      *through* a container is B4c's job once images exist.

## Relevant files

- `harness/sut_process.py` — `spawn_sut` becomes container-capable.
- `harness/event_loop.py` — `_run_reset` becomes container-restart.
- `suts/*/sut-manifest.json` — `image` + `env_passthrough` fields.
- `docs/sut-interface.md` — Invocation section.
- `tests/test_no_state_fake_anthropic.py` and siblings — confirm the
  no-`image` path still works.

## Decisions already made

(From the 2026-05-30 B4-refinement conversation; full context in
`.tasks/debriefs/B4.md`.)

- **DooD over DinD.** Dev container mounts the host docker.sock; SUT
  containers are host siblings. Path translation is therefore required
  for any host→container bind mount.
- **Bind mounts + optional `HOST_WORKSPACE`, not named volumes.** The
  harness snapshots `DIR` by reading it directly off the host filesystem
  (`harness/dir_lifecycle.py:snapshot_dir` — `rglob` + `tarfile`). A
  named volume would force a copy-out before every snapshot; a bind
  mount stays directly readable. Bare-host mode needs bind mounts
  anyway. In dev-container (DooD) mode, the harness translates the
  dev-container `DIR` path to the host path via a `HOST_WORKSPACE` env
  var the dev container sets; outside a dev container, no translation.
  The same translation covers the option-B shim mount.
- **Generic manifest-declared env passthrough** (see acceptance
  criteria) so B9 stays a manifest-only change.
- **Soft tier enforcement** — record declared vs. actual, don't refuse
  to run. (The recording itself is B4c; noted here so B4a doesn't build
  hard enforcement by accident.)

## Out of scope

- The Dockerfiles themselves — **B4b**.
- Bare-host + dev-container end-to-end smoke validation, `QUICKSTART.md`,
  tier-metadata into `run-manifest.json` — **B4c**.
- Image distribution / registry push — deferred (see B4 parent brief).
- Container-spin-up overhead in `wall_clock_ms` accounting — B4c decides
  whether to record it separately.
- B9 (provider-neutral backend) and B3 (judge) — orthogonal.

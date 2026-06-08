# C12 Non-root SUT containers — stop bind-mount writes landing as root

**Priority:** medium
**Blocked by:** nothing (C9 wired the container launch path)
**Touches:** `harness/sut_process.py`, `retention_bench/system.py`, `suts/*/Dockerfile`, `suts/*.Dockerfile`, `tests/`, `docs/sut-interface.md`

## Context

C9 surfaced that the SUT containers run as **root** (the `python:3.11-slim` base
has no `USER`), so files written to the bind-mounted survive-dir (`/dir`) come
back **root-owned** on the host. Reads are fine, but host-side cleanup that runs
as the `agent` user — notably the `wipe_on_reset` stateless-baseline arm's
`_wipe_survive_dir` — hits `PermissionError` on root-owned files. So container
mode + the stateless arm is unsafe today, and running SUT containers as root is
poor hygiene for a public-credibility artifact.

Decided with Toby (2026-06-08): fix it as the **default across all four SUT
images** (constructive + the three API SUTs), not just constructive.

## Goal

Containerised SUTs run as a **non-root** user and write survive-dir files the
host `agent` user can read *and* delete, by default. Build-verify all four images
run correctly non-root.

## Approach (implementer to confirm)

Prefer **launch-time `--user $(id -u):$(id -g)`** threaded through
`ContainerSpec`/`build_docker_argv` (robust: written files match the host user
regardless of image uid) over a baked `USER` directive (brittle: a fixed image
uid may not match the host). Consider a baked non-root `USER` *as well* for
defense-in-depth (don't run as root even without `--user`), with the launch-time
`--user` overriding to match the host. Watch the no-`/etc/passwd`-entry case
(arbitrary uid → `getpwuid` failures / no `$HOME`); the SUTs only need to import
their installed package and write `/dir`, so this is usually benign — verify.

## Acceptance criteria

- [ ] Container launch runs as a non-root user by default;
      `build_docker_argv` emits the user mapping; subprocess mode unaffected.
- [ ] A containerised SUT's survive-dir writes are owned by the host launching
      user — assert the host can `unlink` a container-written file (the
      stateless-wipe hazard is gone). Docker-gated test.
- [ ] `docker build` + a non-root run succeeds for **all four** SUT images
      (constructive torch image + the three slim API images); wire `image`
      fields into the three API manifests if needed to exercise them.
- [ ] The C9 constructive container e2e still passes under the non-root default.
- [ ] `docs/sut-interface.md` "Launch modes" documents the non-root default +
      the host-uid mapping rationale.

## Relevant files

- `harness/sut_process.py` — `ContainerSpec`, `build_docker_argv`,
  `spawn_sut(container=…)`.
- `retention_bench/system.py` — `ContainerLaunch` / `_build_container_spec`
  (thread the user option if exposed).
- `suts/sut-python-base.Dockerfile`, `suts/sut-torch-cpu-base.Dockerfile`,
  `suts/*/Dockerfile` — optional baked non-root `USER`.
- `tests/test_docker_launch.py`, `tests/test_constructive_container_clbench.py`.

## Decisions already made

- Non-root as the **default for all four images** (not just constructive).
- Launch-time host-uid mapping preferred over a fixed baked uid (re-confirm if a
  reason to prefer baked emerges).

## Out of scope

- The in-context validation SUT (C11; validates in subprocess mode).
- GPU/model-serving containers (see `project_incontainer_docker_sysbox`).

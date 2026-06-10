# Debrief: B4a Harness docker-run launch engine + manifest contract

**Completed:** 2026-05-30
**Commit:** 16bf61b

## What shipped

The harness can now launch a SUT via `docker run` when its manifest declares an
`image`, over the identical JSONL stdin/stdout wire contract as the subprocess
path. Manifests without `image` keep today's bare-subprocess launch (stubs and
all existing tests/SUTs).

- `harness/sut_process.py`:
  - `ContainerSpec` dataclass (image, container_name, dir_host_path, env_names,
    optional shim_host_path).
  - `build_docker_argv()` — pure function building the `docker run -i --rm
    --name … -v DIR:/dir -w /dir -e RETENTION_BENCH_DIR=/dir [-e NAME…] [shim]
    image entrypoint…` argv. Env forwarded **by name only** (`-e NAME`), so
    values never appear in argv/logs.
  - `host_path_for_mount()` — DooD path translation via `$HOST_WORKSPACE`
    (unset → identity; set + path outside repo → raises rather than mounting an
    unresolvable path).
  - `spawn_sut()` gains a `container=` branch; `SUTHandle` carries
    `container_name`; `kill_sut`/`shutdown_sut` call `_force_remove_container`
    (`docker rm -f`).
- `harness/event_loop.py`: `_make_container_spec()` builds the spec from the
  manifest's existing `image`/`env` fields; wired into both spawn sites (initial
  + RESET respawn). `_run_reset` now takes `run_id` for the container name.
- `docs/sut-interface.md`: "Launch modes" section, `image` field row, DooD
  `HOST_WORKSPACE` note, B9 forward-compat note.
- `tests/test_docker_launch.py`: 11 always-on pure-function/wiring tests + 1
  docker-gated round-trip integration test (skips without a daemon).

Full suite green (2 skips: pre-existing live-API test + the new docker
round-trip). `docker info` is unavailable in this dev container, so the
round-trip skipped locally — B4c does the authoritative end-to-end smoke.

## Descoped / deferred

Per the brief, all correctly downstream:
- The Dockerfiles + real `image` tags in manifests — **B4b**. (Deliberately did
  *not* add `image` to the four real manifests: the images don't build yet, and
  adding it would route existing tests/runs onto a docker path with no image.)
- Bare-host + dev-container end-to-end smoke, `QUICKSTART.md`, tier-metadata
  into `run-manifest.json`, container-spin-up-overhead accounting decision —
  **B4c**.

## Design decisions

- **Reused the existing manifest `env` field as the passthrough list** instead
  of adding `env_passthrough` (the brief's working name). All four manifests
  already declare `env`; the harness simply ignored it (it inherited the full
  environment via `os.environ.copy()`). The subprocess path keeps that full-env
  inheritance unchanged — only the container path treats `env` as an
  allow-list. This is the cleaner of the two, and keeps B9 a manifest-only
  change as intended.
- **RESET tears down by name (`docker rm -f`), not just client SIGKILL.** The
  load-bearing correctness point: killing the `docker run` client process does
  not reliably stop the container, which would let a stale container corrupt the
  next invocation's view of `DIR`. Each container gets a unique
  `retbench-<run_id>-<invocation>` name; teardown removes it explicitly.
- **`HOST_WORKSPACE` translation imposes a documented constraint:** in DooD
  mode the run dir must live under the repo root (it does by default). If
  `HOST_WORKSPACE` is set and `DIR` is outside the repo, `host_path_for_mount`
  raises rather than silently bind-mounting a path the host daemon can't
  resolve. Bare-host leaves it unset (identity translation).
- **Test-shim mount is opt-in via `$RETENTION_BENCH_SHIM_DIR`** — the container
  analogue of the subprocess tests' PYTHONPATH-shim trick (option B from the
  split discussion: mount the one shim, no per-SUT `Dockerfile.test`). The
  harness mounts it `:ro` and sets `PYTHONPATH=/shim`. Wiring exists now; a test
  that actually drives a SUT *through* a container using it is **B4c**.
- **Docker round-trip test skips without a daemon**, mirroring the existing
  live-API skip, so CI stays green without docker. Pure-function tests carry
  the argv/translation logic coverage unconditionally.

## Observations

- The `env` field already existed in all four manifests but was dead metadata —
  the harness never read it. B4a is the first code to consume it. Worth knowing
  for B4b (the manifests are already correctly populated for the container path).
- `extra_pythonpath`/`sut_pythonpath` is silently ignored on the container path
  (the SUT package is baked into the image). `__main__` still computes it for
  the subprocess path; harmless to leave passing through.
- The container path's stdin/stdout piping reuses the exact `Popen` machinery —
  `docker run -i` is just another subprocess from the harness's view, so
  `send_event`/`_readline_with_timeout` needed zero changes.

## Follow-ups

### Filed as tasks

- Already filed: **B4b** (Dockerfiles), **B4c** (smoke + tier audit). B4a
  unblocks B4b.

### Considered and dropped

- *Auto-detecting DooD (e.g. probing for `/.dockerenv`) to avoid requiring
  `HOST_WORKSPACE`* — too magic, and the failure mode (unresolvable mount) is
  obscure. Explicit env var with a clear raise-on-mismatch is more auditable.
  Not worth a task.
- *Recording container spin-up time separately from `wall_clock_ms` now* —
  belongs with the run-manifest changes in B4c, where there's an actual
  container to measure. Left to B4c (its brief already lists it).

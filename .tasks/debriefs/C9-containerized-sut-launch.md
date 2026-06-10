# Debrief: C9 Containerized SUT launch for the CL-Bench path

**Completed:** 2026-06-08
**Commit:** aaf29e4

## What shipped

`retention_bench.SubprocessSystem` can now launch its SUT inside a docker
container, reusing the B4a engine (`harness.sut_process`) wholesale — subprocess
launch stays the default, container mode is opt-in.

- **`ContainerLaunch`** dataclass (`image`, `env_names`, `name_prefix`) +
  `SubprocessSystem(container=…)`. `_build_container_spec()` mirrors
  `harness.event_loop._make_container_spec`: per-spawn-unique container name
  (`prefix-<run_token>-NN`), `host_path_for_mount` survive-dir translation, and
  the opt-in `$RETENTION_BENCH_SHIM_DIR` mount. Exported from the package root.
- **`SubprocessSystem.shutdown()` + context-manager + `weakref.finalize`
  backstop.** CL-Bench's runner has no end-of-run hook and never bounces the
  *last* spawned SUT, so without this the final container leaks. `shutdown()`
  reaps it (kill + `docker rm -f`) without touching the reset-semantics counters;
  the finalizer reaps a forgotten handle at GC / interpreter exit.
- The hard RESET teardown needed **zero changes** — `_hard_bounce → kill_sut →
  _force_remove_container` already `docker rm -f`s the container by name; the
  handle carries `container_name` whenever `spawn_sut(container=…)` is used.
- **Manifest:** added `image: retention-bench/sut-constructive:0.1` and
  `clbench_entrypoint: ["python","-m","constructive.clbench_main"]` to the
  constructive manifest (see Design decisions for why both entrypoints are
  recorded).
- **Build-verified** the two base images (`sut-python-base`,
  `sut-torch-cpu-base`) + the constructive SUT image under Docker 29.5.2 / Sysbox
  nested daemon. Constructive image = 1.33GB (torch CPU).
- **Tests:** `tests/test_constructive_container_clbench.py` (docker+image-gated
  end-to-end: containerised constructive SUT through CL-Bench's runner under
  `EveryNInstances(2)`, asserts 3 launches / 2 kills, state survives the kills —
  `read_count==6`, grew once — and no container left for the run token).
  Daemon-free unit coverage added to `test_subprocess_system.py` (subprocess
  default, spec fields, name uniqueness per-spawn and per-instance, shim opt-in,
  shutdown idempotency).
- **Docs:** constructive README container section rewritten (build-verified,
  `ContainerLaunch` usage, entrypoint caveat, Sysbox `HOST_WORKSPACE` no-op);
  `docs/sut-interface.md` "Launch modes" gained a CL-Bench-path note.

Full suite: **118 passed, 1 skipped** (the skip is the pre-existing live-
OpenRouter integration test — no API key — unrelated).

### Acceptance criteria — all met

- ✅ `SubprocessSystem` accepts a container spec and passes `container=` through;
  subprocess mode default + unchanged.
- ✅ Hard RESET tears down the container (`docker rm -f` by name); survive-dir
  (`/dir` bind-mount) persists across the kill (asserted by the e2e test).
- ✅ `HOST_WORKSPACE` translation exercised (unit test: unset → verbatim path);
  Sysbox no-op confirmed + documented.
- ✅ `docker build` succeeds for the two bases + the constructive image.
- ✅ End-to-end container run through CL-Bench under a reset schedule, asserting
  state survives the container kill; skips cleanly without docker/image.
- ✅ `image` field wired into the manifest; force-subprocess opt-out (the
  default) keeps the always-on suite green without a daemon.

## Descoped / deferred

- **The three slim API-SUT images** (`no_state`, `notes_llm`, `naive_rag`) were
  not build-verified or `image`-wired — the brief named the constructive
  (torch-CPU) image as the priority (the C3 reproducibility friction case). They
  remain build-UNVERIFIED from B4b. (`sut-no-state:0.1` exists locally from an
  earlier ad-hoc build, but its manifest has no `image` field and it wasn't
  re-verified here.)
- **`gain_curve` container support.** The C4 driver still constructs
  subprocess-mode systems only; threading `ContainerLaunch` through the sweep is
  out of scope (C4 reporting is explicitly out-of-scope in the brief). The
  `weakref.finalize` backstop already covers its orphaned subprocess handles.
- **Bare-host (non-Sysbox) DooD topology** — validated only on Sysbox per the
  brief; the `HOST_WORKSPACE` path is unit-tested but not run end-to-end on a
  host-socket daemon.
- **Container-run user / file ownership** — see Observations; documented, not
  fixed.

## Design decisions

- **`ContainerLaunch` carries `image`/`env_names`, not a ready-made
  `ContainerSpec`.** The spec's `container_name` and `dir_host_path` are
  per-spawn (unique name) and per-survive-dir, so they can't be fixed at
  construction; the system builds a fresh `ContainerSpec` each `_spawn`. The
  brief offered either form — the stable-parts dataclass is the honest one.
- **Per-instance `run_token` in the container name** (`prefix-<token>-NN`), on
  top of event_loop's run-id+index scheme. Two `SubprocessSystem` instances
  sharing a `name_prefix` (e.g. future gain-curve sweep arms) would otherwise
  collide on `…-00`; the uuid token namespaces each instance's containers.
- **`shutdown()` does not increment `kills`/`scheduled_resets`.** Those counters
  track the reset *schedule* (tests assert `kills==2`); end-of-run teardown is
  plain cleanup, so it's deliberately uncounted. Added a `weakref.finalize`
  backstop (holding a mutable handle-box, not `self`) so a forgotten `shutdown()`
  still reaps — important for a public-credibility artifact where a leaked 1.3GB
  container is worse than a leaked file.
- **Recorded `clbench_entrypoint` in the manifest** rather than overwriting the
  book-track `entrypoint`. The constructive SUT has two live wire contracts from
  one codebase; the manifest now documents both machine-readably instead of
  silently pointing at the wrong one for the CL-Bench path.
- **The e2e test does not build the image** (a ~1.3GB torch build) — it skips
  unless the image is already present, so the always-on suite never triggers a
  slow network build. Build is a documented manual/CI step.

## Observations

- **"CL-Bench owns packaging" was only half-true (confirmed).** As the brief's
  C3 finding predicted, CL-Bench launches *systems* in-process and has no
  equivalent of B4a's "containerised external-process SUT + DIR bind-mount +
  RESET-via-container-kill." `SubprocessSystem` + the B4a engine genuinely owns
  this; the wiring was small precisely because the engine already existed.
- **The stale manifest entrypoint was the real trap, not the build.** The
  manifest/Dockerfile point at `python -m constructive` (book-track READ/QUIZ),
  but `SubprocessSystem` speaks the C2 `prompt`/`action` protocol —
  `python -m constructive.clbench_main`. A green `docker build` alone would have
  left a container that talks the wrong protocol. Caught in the brief re-read
  pass; the e2e test pins the correct entrypoint.
- **The hook-less runner leaks the final SUT.** First container run left exactly
  one container alive (the last, un-bounced spawn). Benign as an orphan
  subprocess (why C3 never noticed), a real leak for containers. Hence
  `shutdown()` + the finalizer.
- **Container writes are root-owned.** The image runs as root, so
  `/dir/checkpoint.pt` lands root-owned on the (agent-owned) host survive-dir.
  Read-back (`torch.load`) is fine (world-readable), and the stateful retention
  path only needs persistence. But the host-side `wipe_on_reset` cleanup
  (`_wipe_survive_dir`, runs as `agent`) would hit `PermissionError` on
  root-owned files — so the **stateless-baseline arm is not container-safe**
  today. The e2e test uses the stateful arm and sidesteps this. Fix would be
  `docker run --user $(id -u)` or a root-side wipe; filed as a follow-up.
- **`numpy` not in the image** → a harmless "Failed to initialize NumPy" warning
  from torch on import; the SUT path doesn't use numpy and runs fine.
- **Build cost:** torch-CPU base ~24s (cached layers helped); constructive image
  ~0.3s on top. Each SUT spawn is a `docker run` of the local 1.33GB image;
  the 6-instance / 3-spawn e2e completes in ~6s.

## Follow-ups

### Filed as tasks

None filed — the items below are either covered by existing tasks or too small
to gate. (Flagging here for the next session to confirm rather than auto-filing.)

### Considered and dropped

- *File a "container-safe stateless arm (`--user` / root-side wipe)" task.* Real
  (the wipe arm can't run in container mode today), but narrow and only bites if
  someone containerises the stateless baseline — which the gain-curve driver
  doesn't do (subprocess-mode arms). Documented above; re-raise if container
  mode reaches the wipe arm. Not worth a standing task yet.
- *Build-verify + `image`-wire the three API SUT images.* Out of the C9 priority
  (constructive was the reproducibility case). Mechanical once someone needs the
  API SUTs containerised; lives naturally in whatever task first runs them in
  containers, not a standalone chore.
- *`gain_curve` container support.* Belongs with a future reporting task if/when
  a containerised sweep is wanted; C4 is closed and this isn't load-bearing.

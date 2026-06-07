# C9 Containerized SUT launch for the CL-Bench path (revive + build-verify B4a/B4b)

**Priority:** medium
**Blocked by:** nothing (C3 done; engine + Dockerfiles already exist)
**Touches:** `retention_bench/system.py`, `suts/*/Dockerfile`, `suts/*.Dockerfile`, `suts/*/sut-manifest.json`, `tests/`

## Context

A DooD/container launch engine for SUTs already exists from the pre-pivot
book-track work but is **unwired and unverified** in the current CL-Bench path:

- **B4a (`16bf61b`)** — `harness/sut_process.py` has `ContainerSpec`,
  `build_docker_argv` (`docker run -i --rm`, DIR bind-mounted to `/dir`, env
  forwarded **by name**, kill via `docker rm -f`), and `host_path_for_mount` +
  `HOST_WORKSPACE` for DooD host-path translation. `spawn_sut(..., container=...)`
  has a full container branch alongside the subprocess branch.
- **B4b (`51f6625`)** — four SUT Dockerfiles (`no_state`, `notes_llm`,
  `naive_rag`, `constructive`) + two base images (`sut-python-base`,
  `sut-torch-cpu-base`). **Build-UNVERIFIED** — committed when this container had
  no Docker daemon, so no `docker build` ever ran against them.
- **B4c** — the task that would have build-verified + wired this was
  **superseded by the clbench-pivot** on the rationale "CL-Bench owns packaging."

Two things have since changed that reopen this:

1. **Docker now works here** — Sysbox nested `dockerd`, verified 2026-06-03
   ([[project_incontainer_docker_sysbox]]). The original B4c blocker is gone.
2. **C3 surfaced the reproducibility friction** the engine was meant to solve:
   the constructive SUT needs `torch`, which had to be hand-installed into the
   cl-bench venv (it was missing everywhere). A containerized SUT carries its own
   deps; relevant to the public-credibility goal ([[project_cleval_dual_purpose]]) —
   a reviewer should be able to run the exact SUT env.

**Crucial finding (C3 wrap-up, verified):** "CL-Bench owns packaging" is only
half-true. CL-Bench launches *systems* **in-process** — the runner holds a
`ContinualLearningSystem` instance and calls `.respond()`/`.observe()`/`.reset()`
directly (`runner.py:240,261,426`); the CLI instantiates a system *class* from
the registry. Its Docker helpers (`src/systems/common.py`:
`start_docker_container`/`docker_exec`) are for a *system's own workspace* (e.g.
the `codex` agent runs its CLI in a per-run container) — an opt-in helper, **not**
a framework feature that containerizes arbitrary external-process SUTs. There is
no CL-Bench equivalent of B4a's "containerized external SUT + DIR bind-mount +
hard-RESET via container kill." That is genuinely ours to own. `SubprocessSystem`
is the bridge to external-process SUTs, and it currently calls `spawn_sut(...)`
**without** `container=` (`system.py:124`) — so every SUT runs as a bare host
subprocess.

## Goal

Make `retention_bench.SubprocessSystem` able to launch its SUT in a Docker
container (reusing the B4a engine), build-verify the B4b Dockerfiles now that
Docker works, and prove a containerized constructive SUT runs through CL-Bench's
runner under a hard RESET with the survive-dir bind-mounted.

## Acceptance criteria

- [ ] `SubprocessSystem` accepts an optional container spec (e.g.
      `image=...`/`env_names=...` or a `ContainerSpec`) and passes `container=`
      through to `spawn_sut`; subprocess mode stays the default and unchanged.
- [ ] The hard RESET (`_hard_bounce`) correctly tears down the **container**
      (`docker rm -f` by name via the existing kill path), not just a client
      process; the survive-dir (`/dir` bind-mount) persists across the kill.
- [ ] `HOST_WORKSPACE` path translation is exercised/validated for this
      container topology (Sysbox nested daemon shares the FS, so translation is
      likely a **no-op** here — confirm and document; see the dev-env memory).
- [ ] `docker build` succeeds for the two base images + at least the
      `constructive` SUT image (the torch-CPU one — highest reproducibility
      payoff and the C3 friction case).
- [ ] An end-to-end test runs the constructive SUT **in its container** through
      the CL-Bench runner on `blind_spectrum_monitoring` under a reset schedule,
      asserting state survives the container kill (mirrors
      `tests/test_constructive_clbench.py`). Skips cleanly when Docker absent.
- [ ] Wire an `image` field into the SUT manifests (or document how the run
      selects container vs subprocess); a force-subprocess opt-out keeps the
      always-on tests green without a daemon.

## Relevant files

- `retention_bench/system.py` — `_spawn`/`_hard_bounce`; add the container path.
- `harness/sut_process.py` — `ContainerSpec`, `build_docker_argv`,
  `host_path_for_mount`, `spawn_sut(container=...)`, `kill_sut` (reuse as-is).
- `suts/sut-python-base.Dockerfile`, `suts/sut-torch-cpu-base.Dockerfile`,
  `suts/constructive/Dockerfile` (+ the other three SUT Dockerfiles).
- `suts/*/sut-manifest.json` — `image` field.
- `tests/test_constructive_clbench.py` — model the new container test on it.
- `.tasks/debriefs/B4b.md`, `.tasks/B4c-smoke-and-tier-audit.md` — the original
  (book-track) brief + caveats; mine for the smoke/tier-audit details, but
  retarget from the harness CLI to the `SubprocessSystem` path.

## Decisions already made

- **Reuse the B4a engine in `harness/sut_process.py`**, not CL-Bench's
  `src/systems/common.py` helpers. Ours fits the hard-RESET model (DIR bind-mount
  to `/dir`, env-by-name, RESET = `docker rm -f`); CL-Bench's are workspace
  helpers for in-process agent systems. (Re-confirm if the implementer finds a
  reason to prefer CL-Bench's.)
- **Subprocess mode stays the default.** Container mode is opt-in so the
  daemon-free test suite stays green.
- **Constructive (torch-CPU) image is the priority build-verify target** — it's
  the reproducibility win and the C3 friction case; the three slim API images are
  secondary.

## Out of scope

- GPU / model-serving containers (this is CPU SUTs; the GPU split is a separate
  open question — see [[project_incontainer_docker_sysbox]]).
- A bare-host (non-Sysbox) DooD topology — validate here on Sysbox; note any
  host-path-translation differences for a future bare-host run.
- Reset-axis curve reporting (C4) and the drift-schedule corpus (C4 follow-up).

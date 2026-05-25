# B4 Docker container packaging + tier-declaration scaffolding

**Priority:** medium (raised when there are 3+ SUTs or when external
contributors need a reproducible packaging story, whichever comes first)
**Blocked by:** B2 (file second stateful SUT first; the container
contract should generalise across at least 3 concrete SUTs, not be
designed around the first one)
**Touches:** `suts/*/Dockerfile`, `harness/sut_process.py`,
`harness/event_loop.py` (subprocess → docker run), `docs/sut-interface.md`,
`docs/decisions-checklist.md` (tier-declaration), `pyproject.toml`,
possibly `docs/QUICKSTART.md` (new file).

## Context

Per decision #16, SUTs declare a `hardware_tier` in `sut-manifest.json`
(`consumer | 1xH100 | 8xH100 | API | open`). Today the declaration is
trust-only: SUTs assert their tier in the manifest and the harness
records it but doesn't enforce. B4 is where tier-declaration gets
real scaffolding: SUTs ship as Docker images, the harness launches
them via `docker run`, and image build / hardware-tier metadata flow
through the trace as audit-able artifacts.

B4 also incidentally fixes the dev-env pain that surfaced during B1
(notes-llm install required `--break-system-packages`; three SUTs
share one Python install). Near-term we're papering over with per-SUT
venvs or `--break-system-packages`; B4 retires that workaround.

This task was discussed and scoped at the end of the B1 / sample-output
session on 2026-05-25. Key prior conversation captured under "Decisions
already made" below.

## Goal

Each SUT under `suts/<name>/` ships with a Dockerfile that builds a
self-contained image. The harness launches the SUT by running the
image (`docker run -i --rm ...`) with stdin/stdout piped, same wire
contract as today (JSONL events). The harness works equally well from
inside the dev container (via DooD — host docker.sock mounted) and
from a bare host with just Docker installed. The image build is
cacheable; CI builds and (optionally) pushes images.

## Acceptance criteria

- [ ] `suts/no_state/Dockerfile`, `suts/notes_llm/Dockerfile`,
      `suts/naive_rag/Dockerfile` (assuming B2 has landed) — minimal,
      self-contained, slim base, reproducible.
- [ ] `sut-manifest.json` gains an `image` field (or similar) so the
      harness knows what to `docker run`. Existing `entrypoint` field
      reinterpreted as the in-container argv if needed.
- [ ] Harness launches the SUT via `docker run -i --rm` (or compatible
      `subprocess` wrapping) and pipes stdin/stdout identically to
      today's `Popen` path. `RESET` still works (container is
      killed and a fresh one is spawned, mirroring today's subprocess
      lifecycle).
- [ ] `DIR` is mounted into the container. Path translation gotcha
      (see "Open questions") documented and worked around for the
      DooD case.
- [ ] **Bare-host smoke test:** `./run.sh smoke` works on a host with
      only Docker installed (no Python venv on the host, no dev
      container) — verified end-to-end at least once and documented
      in `docs/QUICKSTART.md`.
- [ ] **Dev-container smoke test:** `./run.sh smoke` works from
      inside this dev container with DooD configured (host
      docker.sock mounted in). No regression vs today's run.
- [ ] Hardware-tier metadata flows from `sut-manifest.json` into
      `run-manifest.json`; what the SUT declared and what the host
      actually exposed (e.g. visible GPUs) both recorded for audit.
- [ ] `--break-system-packages` and per-SUT venvs become unnecessary
      (the workaround is documented as deprecated; README updates
      across SUTs to point at the container path).
- [ ] All existing tests still pass (the fake-anthropic shim path may
      need rethinking — see open question below).

## Decisions already made (2026-05-25 conversation)

- **B4 is benchmark-side first, dev-env-side second.** The
  motivation is reproducibility-for-consumers and tier-declaration
  machinery; the dev-env cleanup is a side benefit. Scope decisions
  should favour the benchmark-consumer use case when they trade
  off against developer ergonomics.
- **Must work from a bare host.** Not everyone runs this in a
  dev container with DooD; the benchmark needs to be runnable by
  anyone with Docker installed. This is a hard requirement, not a
  nice-to-have, and warrants its own smoke-test path.
- **Defer until B2 has landed.** Containerizing three concrete SUTs
  at once is a better design path than containerizing one and
  retrofitting two. The container contract should generalise across
  at least one no-DIR + one notes-style + one index-style SUT.

## Open questions to scope before starting

1. **Base image strategy.** `python:3.11-slim` per SUT? Multi-stage
   builds (builder + runtime) for smaller images? A shared base
   image (`retention-bench/sut-python-base`) that SUT Dockerfiles
   extend?
2. **DooD path-translation gotcha.** When the dev container mounts
   the host's docker.sock, the daemon's view of paths differs from
   the dev container's view. `docker run -v $DIR:/dir` from inside
   the dev container will use the dev-container path, which the
   host daemon may not be able to resolve. Options: detect
   dev-container mode and translate; require dev users to set a
   `HOST_WORKSPACE` env var; use named volumes instead of bind
   mounts; only require bind-mount support outside-container.
3. **Image distribution.** Local-build-only (every user `docker
   build`s)? Push to a registry (Docker Hub, GHCR)? CI-built and
   tagged per commit? Affects reproducibility story and CI complexity.
4. **Tier-declaration enforceability.** A SUT can claim
   `hardware_tier: API` and then secretly use a local GPU.
   Enforcement options: hard (refuse to run if declared tier
   doesn't match host capabilities), soft (record both and let
   auditors compare), or trust-only (today's behaviour, just
   recorded). Probably soft — but worth deciding.
5. **Fake-anthropic shim under containerization.** Today's shim
   sits on PYTHONPATH inside the SUT subprocess. Under
   containerization, the SUT subprocess is replaced by a docker
   container; the PYTHONPATH trick doesn't survive the container
   boundary. Options: build a "test image" variant per SUT that
   bakes the shim in; mount the shim in via `-v` and set
   PYTHONPATH; keep integration tests on the non-container code
   path (live-API or stub) and accept that container path has
   fewer integration tests.
6. **Resource accounting.** `wall_clock_ms` is harness-measured
   today; under containerization it now includes container spin-up
   time. Decide whether to record container-overhead separately.

## Relevant files

- `suts/no_state/`, `suts/notes_llm/` (and `suts/naive_rag/` once
  B2 lands) — Dockerfiles go here.
- `suts/no_state/sut-manifest.json` — image field schema lives here.
- `docs/sut-interface.md` — Invocation section needs updating to
  describe `docker run`-based launch.
- `harness/sut_process.py` — `spawn_sut` becomes container-based.
- `harness/event_loop.py` — `_run_reset` becomes container-restart.
- `tests/test_no_state_fake_anthropic.py`,
  `tests/test_notes_llm_fake_anthropic.py` — affected by the
  shim-under-containerization question.

## Out of scope

- LLM-judge scorer (B3) — separate task; orthogonal.
- Generic LLM-backend abstraction (B9) — separate task; orthogonal.
- Multi-host scheduling (running multiple SUTs in parallel on
  different physical machines). The benchmark is local-first for
  now; multi-host is a hypothetical future concern.
- Kubernetes / docker-compose orchestration. A single `docker run`
  per SUT is enough.
- Pushing images to a public registry as part of CI. Worth doing
  later for distribution, but the first cut should build-locally
  to keep CI complexity down.
- Image signing / SLSA provenance. Important if/when the benchmark
  has external contributors submitting SUT images, but premature
  while we're still authoring the reference set.

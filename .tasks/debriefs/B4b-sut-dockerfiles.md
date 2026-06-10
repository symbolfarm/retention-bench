# Debrief: B4b SUT Dockerfiles + workaround deprecation

**Completed:** 2026-05-30
**Commit:** 51f6625

## What shipped

Reproducible container images for all four reference SUTs, satisfying the B4a
launch contract (manifest `entrypoint` = in-container argv, workdir `/dir`,
package importable in the image).

- `suts/sut-python-base.Dockerfile` — shared slim base (`python:3.11-slim` +
  `anthropic>=0.39.0,<1`), built once and extended by the three API SUTs.
- `suts/sut-torch-cpu-base.Dockerfile` — separate CPU-only torch base
  (`torch>=2.1,<3` from the PyTorch CPU wheel index) for constructive.
- `suts/{no_state,notes_llm}/Dockerfile` — `FROM` the shared base, install the
  package `--no-deps` (anthropic already in the base layer).
- `suts/naive_rag/Dockerfile` — `FROM` the shared base, install
  `.[sentence-transformers]` (real transitive deps, so NOT `--no-deps`), and
  pre-fetch `all-MiniLM-L6-v2` so the container runs offline.
- `suts/constructive/Dockerfile` — `FROM` the torch base, install `--no-deps`.
- Five `.dockerignore` files for build-context hygiene.
- "Container image" README sections on all four SUTs with build commands + the
  `--break-system-packages` workaround note + a pointer to B4c for harness
  auto-launch.

Test suite green (2 pre-existing skips). No harness code touched.

## Descoped / deferred

- **Manifest `image` fields — moved to B4c** (the load-bearing sequencing
  decision; see below).
- **Build verification — NOT done.** No docker daemon in this dev container
  (`docker info` → not found). The "each image builds locally" acceptance
  criterion is therefore **UNVERIFIED**. Real build + run validation is B4c's
  job in a docker-capable environment. Statically verified what was checkable:
  no `pyproject.toml` references a `readme` (so the omitted README won't break
  `pip install .`), packages use setuptools `find`, layer ordering is sane.
  Genuinely unverifiable here: live wheel resolution for anthropic / CPU-torch
  / sentence-transformers against their indexes.
- llama-cpp embedder default — not baked in (per brief escape hatch; see below).

## Design decisions

- **Option-1 sequencing: `image` fields land in B4c, not B4b.** Adding `image`
  to the four real manifests would route the *always-on* fake-anthropic
  integration tests (`test_{no_state,notes_llm,naive_rag}_fake_anthropic`,
  `test_constructive_integration`) onto the docker path, which fails with
  `FileNotFoundError: docker` in any daemonless environment — violating the
  green-suite requirement. B4a's launch path triggers container mode on the
  *mere presence* of `image` (`event_loop._make_container_spec`) with no opt-out.
  The reconciliation (a harness force-subprocess opt-out + a container-path
  shim test) lives in B4c's `Touches`, not B4b's. So B4b ships images only; the
  `image` additions move to B4c to land atomically with that opt-out. (The
  subagent that started B4b correctly stopped and surfaced this rather than
  guessing; decision made by the dispatcher.)
- **Two base images** (shared slim API base + separate torch-CPU base) — per
  the 2026-05-30 split decision; keeps the API trio light.
- **naive_rag stays on `sentence-transformers`, not llama-cpp.** llama-cpp-python
  needs a native gcc/cmake build *and* a GGUF model file absent from the repo —
  both fight a clean reproducible build. The image installs the
  sentence-transformers extra and pre-fetches the MiniLM model for offline runs.
  The flip remains a one-line `NAIVE_RAG_EMBEDDER=llama-cpp` override. (Brief
  explicitly permitted leaving the default if llama-cpp fought the build.)
- **`--no-deps` for no_state/notes_llm/constructive** so the child layer doesn't
  re-resolve the base-provided dependency (and, for constructive, doesn't pull
  the CUDA torch wheel from default PyPI). naive_rag omits it because its extra
  carries real transitive deps.
- **Image tags** `retention-bench/sut-{no-state,notes-llm,naive-rag,constructive}:0.1`,
  bases at `:0.1`.

## Observations

- The README workaround language (`--break-system-packages`) was operational,
  not previously documented — the existing READMEs only had `pip install -e .`.
  Added the note rather than "deprecating" a documented step that didn't exist.
- READMEs deliberately do not claim harness-driven container runs work yet —
  they point at B4c for that wiring — to keep docs honest about what's runnable.

## Follow-ups

### Filed as tasks

- **B4c** (already filed) absorbs two things this task surfaced, both already in
  its `Touches`/criteria but worth making explicit:
  1. Add the `image` field to all four `sut-manifest.json` files.
  2. Add a harness **force-subprocess opt-out** (e.g. `RETENTION_BENCH_FORCE_SUBPROCESS=1`,
     or point the existing fake-anthropic tests at a no-`image` path) so the
     always-on integration tests keep passing once manifests declare `image`.
     Without this, adding `image` reds the suite in daemonless environments.
  B4c must also do the real `docker build` verification deferred here.

### Considered and dropped

- *Multi-stage builds to shrink images* — the brief lists it as optional and not
  required; current single-stage images are already cache-friendly. Not worth it
  before we can even measure image size (no daemon). Drop.

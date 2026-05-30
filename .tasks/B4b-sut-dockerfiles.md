# B4b SUT Dockerfiles + workaround deprecation

**Priority:** medium
**Blocked by:** B4a (the launch engine defines the `image`/`entrypoint`/
`env_passthrough` contract these Dockerfiles must satisfy)
**Touches:** `suts/no_state/Dockerfile`, `suts/notes_llm/Dockerfile`,
`suts/naive_rag/Dockerfile`, `suts/constructive/Dockerfile`,
`suts/*/sut-manifest.json` (image tag), `suts/*/README.md`

## Context

Split from B4 (see `.tasks/debriefs/B4.md`). B4a teaches the harness to
launch a containerised SUT; this task provides the images for it to
launch. There are now **four** reference SUTs, not the three the
original B4 brief named — `suts/constructive/` (the train-and-grow
transformer, B13) landed after B4 was filed and has a materially
different install surface (CPU `torch`, ~1GB) from the three
API-only SUTs.

## Goal

Each SUT under `suts/<name>/` ships a minimal, self-contained,
reproducible Dockerfile that builds an image the B4a launch path can
run. The `--break-system-packages` / per-SUT-venv workaround from B1
becomes unnecessary and is documented as deprecated.

## Acceptance criteria

- [ ] `suts/no_state/Dockerfile`, `suts/notes_llm/Dockerfile`,
      `suts/naive_rag/Dockerfile` — **shared slim base.** The three
      API SUTs all want `python:3.11-slim` + the `anthropic` SDK; build
      a small shared base (e.g. `retention-bench/sut-python-base`) that
      these three extend, so the common layer is built once.
- [ ] `suts/constructive/Dockerfile` — **separate torch-CPU base.** Do
      NOT fold torch into the shared API base; keep the API trio light
      at the cost of one extra Dockerfile (decided 2026-05-30). Pin
      CPU-only torch.
- [ ] Each `sut-manifest.json` `image` field points at the tag its
      Dockerfile produces; argv/entrypoint matches B4a's contract.
- [ ] Images are reproducible and cacheable (pinned bases, ordered
      layers so dependency installs cache independently of source).
- [ ] naive_rag: this is the point to flip its default embedder to the
      llama-cpp path (per the original B4 brief note) if that's clean to
      bake into the image; if it fights the build, note it and leave the
      `sentence-transformers` default — don't let it block the trio.
- [ ] `--break-system-packages` / per-SUT venv workaround documented as
      deprecated; each affected SUT `README.md` points at the container
      path instead.
- [ ] Each image builds locally (`docker build`) — full end-to-end
      *run* validation through the harness is B4c, but each image must
      at least build clean here.

## Relevant files

- `suts/no_state/`, `suts/notes_llm/`, `suts/naive_rag/`,
  `suts/constructive/` — Dockerfiles + manifest image tags + READMEs.
- `suts/*/pyproject.toml` — dependency sources the images install from
  (constructive pins torch-CPU in its own pyproject per B13 convention).

## Decisions already made

(From the 2026-05-30 B4-refinement conversation; full context in
`.tasks/debriefs/B4.md`.)

- **Two base images, not one.** Shared slim base for the three API
  SUTs; a separate torch-CPU base for constructive. Keeps the common
  case light; the extra Dockerfile is an accepted cost.
- **Build-locally first.** No registry push / CI image publication in
  this task (deferred per parent B4 brief). Each user `docker build`s.

## Out of scope

- Harness launch/reset logic — **B4a**.
- Smoke validation, `QUICKSTART.md`, tier-metadata audit flow — **B4c**.
- Registry push, image signing, SLSA provenance — deferred (parent B4).
- Multi-stage build micro-optimisation beyond "reproducible + cacheable"
  — fine to do if cheap, not a requirement.

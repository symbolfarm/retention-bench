# Debrief: B4 Docker packaging + tier scaffolding — SPLIT

**Split:** 2026-05-30
**Superseded by:** B4a, B4b, B4c
**Commit:** (this split commit)

## Why split

B4 bundled three separable concerns — the harness docker-run launch
engine, four SUT Dockerfiles, and the end-to-end smoke + tier-audit
work — behind ~9 acceptance criteria spanning the harness, every SUT,
docs, and tests. That's comfortably more than one session's attention
without compaction, which the task-cycle skill treats as a smell. Split
into a clean dependency chain:

- **B4a** — harness docker-run launch path + RESET-as-container-restart
  + DIR/shim mount + manifest `image`/`env_passthrough` contract. The
  engine. Validatable against a stock public image + existing tests, so
  it doesn't block on B4b.
- **B4b** — the Dockerfiles (shared slim base for the API trio; separate
  torch-CPU base for constructive) + workaround deprecation. Blocked by
  B4a (needs the launch contract).
- **B4c** — bare-host + dev-container smoke paths, `QUICKSTART.md`,
  tier-metadata into `run-manifest.json`, container-path integration
  coverage. Blocked by B4a + B4b.

## Refinements folded into the children (2026-05-30 conversation)

These came out of talking through the original brief's open questions
with Toby before splitting:

1. **Stale SUT count.** Original brief named three SUTs; `suts/constructive/`
   (B13, train-and-grow transformer) landed afterward and has a
   materially heavier install surface (CPU torch, ~1GB). Now a
   first-class target in B4b.
2. **Two base images, not one.** Shared slim base for the three API
   SUTs; separate torch-CPU base for constructive. Keeps the common
   case light; the extra Dockerfile is an accepted cost. (B4b)
3. **B4 before B9.** B9 (provider-neutral LLM backend) is still an
   unscoped backlog one-liner and is design-heavy (which abstraction;
   does it subsume the embedder seam). Its coupling to B4 is shallow —
   two narrow seams (the `pip install anthropic` line in 3 Dockerfiles,
   and the harness env passthrough). Resolved by making B4a's env
   passthrough **manifest-declared and generic** (no hardcoded
   `ANTHROPIC_API_KEY`/`<SUT>_MODEL` in harness code), so B9 later
   becomes a manifest-only change with no harness edit.
4. **Fake-anthropic shim under containers → option B (mount the shim).**
   Tests run the real image with `-v shim:/shim:ro -e PYTHONPATH=/shim`;
   production launches add neither. One shim source of truth; no
   `Dockerfile.test` per SUT (rejected A as over-engineered for an
   artifact we never ship; rejected C — keep tests off the container
   path — because it re-opens the integration gap B10 was built to
   close). Mount mechanism built in B4a; exercised by a container-path
   test in B4c.
5. **DooD path translation → bind mounts + optional `HOST_WORKSPACE`.**
   Confirmed `harness/dir_lifecycle.py:snapshot_dir` reads `DIR`
   directly off the host filesystem (`rglob` + `tarfile`); a named
   volume would force a copy-out before every snapshot, so bind mounts
   win. Dev-container (DooD) mode translates the dev-container `DIR`
   path to the host path via `HOST_WORKSPACE`; bare-host needs no
   translation. Same translation covers the shim mount. (B4a defines,
   B4c exercises.)
6. **Soft tier enforcement** — record declared vs. actual, don't
   hard-refuse on mismatch. (B4c lands the recording; B4a told not to
   build hard enforcement by accident.)

## Carried-forward out-of-scope (unchanged from parent)

Registry push / CI image publication, image signing / SLSA provenance,
multi-host scheduling, k8s/compose orchestration — all still deferred.
Distributed across the children's Out-of-scope sections.

## Follow-ups

None new — this is a pure split. The children carry the work.

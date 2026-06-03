# B16 Boundary token-counting proxy (measured, not self-reported)

**Priority:** medium
**Blocked by:** nothing
**Touches:** `harness/`, `harness/event_loop.py`, `docs/sut-interface.md`, `docs/trace-schema.md`

## Context

Today the harness trusts each SUT to **self-report** its own token usage
(`tokens_in`/`tokens_out`/`api_call_count` on every reply;
`harness/event_loop.py` accounting just sums what the SUT hands back). For a
benchmark that is also a **public-credibility artifact** (see the CL-eval
dual-purpose framing), "we trust the system under test to report its own
resource use" is a reviewer's first line of attack: a SUT could under-report
to look cheaper on the cost axis, and nothing in the trace would catch it.

B9 created the unlock: every text SUT now reads an optional
`RETENTION_BENCH_BASE_URL` and points its `openai` client there. That means the
harness can stand up a **local proxy** that forwards to OpenRouter (or wherever),
tallies real `usage` at the boundary, and hands the SUTs that proxy's URL —
shifting token accounting from "trust the SUT" to "measured at the wire."

## Goal

A harness-owned proxy that sits between the SUT and the upstream
OpenAI-compatible endpoint, counts tokens/calls at the boundary, and writes a
boundary-measured resource record into the run dir that can be compared against
(or supersede) the SUT self-report.

## Acceptance criteria

- [ ] A local forwarding proxy (OpenAI-compatible passthrough) the harness can
      launch for a run, configured via the upstream `base_url` + key.
- [ ] Harness injects the proxy URL into the SUT env as `RETENTION_BENCH_BASE_URL`
      (and the real upstream key stays harness-side, not handed to the SUT — a
      nice security side-benefit).
- [ ] Boundary-measured `usage` (prompt/completion tokens, call count, per model)
      written to the run dir; reconciled against the SUT self-report.
- [ ] Discrepancy between self-report and boundary-measure is surfaced (a trace
      field or a warning), not silently dropped — that delta is itself a finding.
- [ ] Works for the containerised launch path too (proxy reachable from inside
      the SUT container; mind the docker network seam).
- [ ] Tests pass; a fake-upstream test exercises the count-at-boundary path.

## Relevant files

- `harness/event_loop.py` (resource accounting; ~line 103)
- `harness/sut_process.py` (env injection; container networking)
- `docs/sut-interface.md`, `docs/trace-schema.md` (document the new record)

## Decisions already made

- The `RETENTION_BENCH_BASE_URL` override seam exists (B9) specifically to enable
  this; B13 builds the proxy that seam was left for.
- Self-report is **not** removed — boundary-measure is the trusted figure;
  self-report stays so the *delta* between them is auditable.

## Out of scope

- Rate-limiting / caching / retry policy in the proxy (keep it a thin counter).
- Embedding-call accounting (naive-RAG's local embedder doesn't go through this).

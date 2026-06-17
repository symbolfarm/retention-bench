# Debrief: C8 Multi-step (turn-taking) SUT adapter for agentic CL-Bench tasks

**Completed:** 2026-06-17
**Commit:** queue cleanup commit

## What shipped

C8 was superseded without implementation. The agentic multi-step adapter remains
a valid future direction, but it is no longer the next target while the project
is focused on small deterministic curriculum substrates for constructive
retention.

## Descoped / deferred

No adapter work landed here. A future agentic CL-Bench adapter should be filed
fresh when the project is ready to target multi-step tasks such as
`exploitable_poker`.

## Design decisions

- Do not keep the multi-step adapter as an active near-term task while
  constructive SUT development and the one-shot curriculum substrate are the
  active research path.
- Preserve the old brief in git history and this debrief rather than deleting
  the idea entirely.

## Observations

The C8 brief's technical notes are still useful, especially the distinction
between transport, wire schema, and per-SUT turn-taking behavior. The priority
changed, not the underlying analysis.

## Follow-ups

Nothing filed now. Re-file a smaller agentic-adapter task when a concrete
multi-step CL-Bench target becomes active again.

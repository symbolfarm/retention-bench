# Debrief: B14 Open-model judge quality validation (SUPERSEDED)

**Superseded:** 2026-06-07
**Commit:** (none — work not done)

## What happened

Obsoleted by the CL-Bench pivot. B14 would validate our LLM-judge's agreement
with a reference judge/human labels. Under the pivot we adopt CL-Bench's
objective, task-defined reward functions and retire our gold-answer + LLM-judge
scoring entirely (`scorer/judge.py`). There is no judge left to validate.

## Disposition

Dropped, not migrated. The underlying concern (scoring credibility) is better
served by CL-Bench's verifiable rewards than by validating a judge.

## Follow-ups

None.

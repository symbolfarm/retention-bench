# Debrief: B16 Boundary token-counting proxy (SUPERSEDED)

**Superseded:** 2026-06-07
**Commit:** (none — work not done)

## What happened

Obsoleted by the CL-Bench pivot. B16 would interpose a wire-level proxy to
reconcile SUT-self-reported token usage against measured usage, for our own
resource appendix. Under the pivot, CL-Bench owns cost/token accounting
(`UsageEvent`, litellm pricing), so the harness-side token-integrity concern
moves out of our hands for in-context systems.

## Disposition

The residual idea that *does* carry forward: our parametric SUTs report compute
(FLOPs + storage-delta), which CL-Bench has no native notion of. That is folded
into C2 as `UsageEvent` emission (`call_type="compute"`), not a token proxy.

## Follow-ups

Subsumed by C2 (compute UsageEvent accounting).

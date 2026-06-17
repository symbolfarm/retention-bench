# Debrief: C6 Constructive-friendly task with an understanding-vs-stenography reward

**Completed:** 2026-06-17
**Commit:** supersede commit

## What shipped

C6 was superseded by RB-2. The retained idea is still valuable, but the framing
changed from an optional fallback task after CL-Bench triage to a first-class
small curriculum substrate for constructive-retention research.

## Descoped / deferred

No task implementation landed here. RB-2 carries the implementation brief.

## Design decisions

- Used a new `RB-` task instead of editing C6 in place so the queue records the
  research pivot explicitly.
- Kept BSM as an external-validity target rather than deleting that path from
  the project.

## Observations

C6 already pointed at the right axis, but its trigger condition was stale: C1
decided BSM was sufficient for CL-Bench integration, while the newer model
strategy needs a smaller developmental benchmark even though BSM remains useful.

## Follow-ups

### Filed as tasks

- **RB-2** Small curriculum task for constructive retention — builds the first
  Retention Bench-owned small curriculum target for the constructive SUT.

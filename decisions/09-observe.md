# Reset only after a completed instance

*The boundary guard*

## Summary

observe() ignores intermediate observations, increments a 1-based
completed-instance count, measures storage, then checks the schedule.

## Why

CL-Bench may emit observations within an instance; resets must occur only at
complete instance boundaries.

## What it buys

Reset ordinals that align with post-reset windows and comparable arm outcomes.

## Trade-off

The implementation depends on CL-Bench's completion predicate and next-query
convention.

## Leads to

observation_marks_instance_complete · reset_ordinals

## Source

```toml
id = "observe"
depth = "implementation"

[source]
path = "retention_bench/system.py"
symbol = "observe"
```

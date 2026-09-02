# Reset only after a completed instance

*The boundary guard*

## Decision

observe() ignores intermediate observations, increments a 1-based
completed-instance count, measures storage, then checks the schedule.

## Context

CL-Bench may emit observations within an instance; resets must occur only at
complete instance boundaries.

## Gains

Reset ordinals that align with post-reset windows and comparable arm outcomes.

## Costs

The implementation depends on CL-Bench's completion predicate and next-query
convention.

## See also

observation_marks_instance_complete · reset_ordinals

## Source

```toml
id = "observe"
depth = "implementation"

[source]
path = "retention_bench/system.py"
symbol = "observe"
```

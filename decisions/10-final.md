# Suppress a reset after the final query

*next_query is not None*

## Decision

Even if the schedule says the final ordinal is a boundary, the harness does
not count a reset when there is no next query to receive it.

## Context

A reset is a discontinuity between instances. Killing after the run cannot
affect an observation and would inflate k.

## Gains

Measured k counts only experimental reset boundaries that can affect
performance.

## Costs

End-of-run process reaping is separate teardown and is intentionally not a
scheduled reset.

## See also

will_reset predicate · shutdown()

## Source

```toml
id = "final"
depth = "implementation"

[source]
path = "retention_bench/system.py"
symbol = "observe"
```

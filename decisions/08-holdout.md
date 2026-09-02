# Hold objects out of bridging

*Not out of teaching*

## Decision

The last object for each attribute is still taught, but is marked holdout so a
write-time shortcut cannot precompute its object→bin answer.

## Context

Without the split, a lookup table over every composed answer can pass transfer
without composing at query time.

## Gains

A held-out transfer number that better reflects composition-generalisation.

## Costs

A sophisticated store can still perform iterative retrieval; whether that
closes the gap is an open empirical question.

## See also

role: holdout · modulo assignment · transfer split

## Source

```toml
id = "holdout"
depth = "mechanism"

[source]
path = "retention_bench/tasks/symbolic_associative_retention.py"
symbol = "_build_instances"
```

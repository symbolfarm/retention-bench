# Hold objects out of bridging

*Not out of teaching*

## Summary

The last object for each attribute is still taught, but is marked holdout so a
write-time shortcut cannot precompute its object→bin answer.

## Why

Without the split, a lookup table over every composed answer can pass transfer
without composing at query time.

## What it buys

A held-out transfer number that better reflects composition-generalisation.

## Trade-off

A sophisticated store can still perform iterative retrieval; whether that
closes the gap is an open empirical question.

## Leads to

role: holdout · modulo assignment · transfer split

## Source

```toml
id = "holdout"
depth = "mechanism"

[source]
path = "retention_bench/tasks/symbolic_associative_retention.py"
symbol = "_build_instances"
```

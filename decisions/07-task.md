# Teach nonce associations, then compose

*Current native task*

## Summary

The task teaches object→attribute facts and attribute→bin rules, then probes
direct recall and two-hop transfer.

## Why

Nonce labels make acquisition during the run explicit and reduce contamination
from prior knowledge.

## What it buys

Exact scoring, analytic chance, and a small bridge from episodic recall to
composition.

## Trade-off

It remains synthetic and supports only the bottom two rungs of the intended
probe ladder.

## Leads to

Recall probes · transfer probes · held-out objects

## Source

```toml
id = "task"
depth = "mechanism"

[source]
path = "retention_bench/tasks/symbolic_associative_retention.py"
symbol = "SymbolicAssociativeRetentionTask"
```

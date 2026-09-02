# Teach nonce associations, then compose

*Current native task*

## Decision

The task teaches object→attribute facts and attribute→bin rules, then probes
direct recall and two-hop transfer.

## Context

Nonce labels make acquisition during the run explicit and reduce contamination
from prior knowledge.

## Gains

Exact scoring, analytic chance, and a small bridge from episodic recall to
composition.

## Costs

It remains synthetic and supports only the bottom two rungs of the intended
probe ladder.

## See also

Recall probes · transfer probes · held-out objects

## Source

```toml
id = "task"
depth = "mechanism"

[source]
path = "retention_bench/tasks/symbolic_associative_retention.py"
symbol = "SymbolicAssociativeRetentionTask"
```

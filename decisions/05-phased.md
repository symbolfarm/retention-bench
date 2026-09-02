# Reset once after learning

*Migration into a durable artifact*

## Decision

A single train/probe-boundary reset removes the volatile episodic store after
learning, then probes what remains in the durable artifact.

## Context

The central consolidation question is not cleanly answered when stores are
erased before learning completes.

## Gains

A direct comparison between no-reset capability and post-store-removal
capability.

## Costs

The SUT must keep its episodic store volatile and persist only the
consolidated artifact, or the protocol degenerates.

## See also

Explicit boundary · volatile store · durable weights

## Source

```toml
id = "phased"
depth = "design"

[source]
path = "docs/phased-store-removal.md"
heading = "The protocol"
```

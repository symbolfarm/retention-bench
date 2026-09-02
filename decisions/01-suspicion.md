# Persisting is not necessarily integrating

*The research suspicion*

## Decision

A system may carry records across sessions yet recompute every useful
abstraction at query time. Retention Bench asks where acquired capability
actually lives.

## Context

Long-lived agents need experience to survive resets, but survival alone can be
satisfied by writing a transcript to disk.

## Gains

A functional distinction between replayable recordings and re-represented
memory.

## Costs

The distinction must be tested through behaviour; storage format alone cannot
prove understanding.

## See also

Hard reset · probe ladder · phased store removal

## Source

```toml
id = "suspicion"
depth = "motivation"

[source]
path = "docs/ROADMAP.md"
heading = "The claim it exists to test"
```

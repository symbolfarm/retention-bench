# Erase working state mechanically

*Why a hard RESET?*

## Decision

The harness kills the SUT process group. A fresh process can inherit only
state that was already persisted in the survive-directory.

## Context

A polite reset method asks the system to forget and cannot rule out hidden
in-memory state.

## Gains

A substrate-neutral discontinuity with an observable persistence boundary.

## Costs

Reloading records is still allowed; RESET exposes its recurring cost rather
than forbidding it.

## See also

Process-group kill · survive-dir · flush-before-reply

## Source

```toml
id = "reset"
depth = "design"

[source]
path = "docs/sut-interface.md"
heading = "Lifecycle"
```

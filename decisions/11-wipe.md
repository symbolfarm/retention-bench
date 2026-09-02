# Wipe durable state only for P

*The stateless arm*

## Summary

On a wiping reset, every survive-dir entry except the reserved .harness
directory is removed; real directories and symlinks take different deletion
paths.

## Why

P must expose each instance to a fresh process with no SUT-created durable
carry-over.

## What it buys

A process-level expression of CL-Bench's stateless baseline.

## Trade-off

Deletion errors are deliberately suppressed; integrity depends on later
behaviour and tests rather than a transactional wipe.

## Leads to

wipe_on_reset · _wipe_survive_dir

## Source

```toml
id = "wipe"
depth = "implementation"

[source]
path = "retention_bench/system.py"
symbol = "_wipe_survive_dir"
```

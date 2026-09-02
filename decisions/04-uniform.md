# Repeat resets during the run

*Graceful degradation*

## Decision

Uniform schedules interleave hard resets with learning and reveal how
performance behaves as disruption accumulates.

## Context

Real agent sessions end repeatedly, not just once after training.

## Gains

A reset-count axis R(k) and post-reset windows that reveal immediate damage.

## Costs

Mid-learning erasure conflates failure to consolidate with lack of time to
learn.

## See also

EveryNInstances · measured k · W(m)

## Source

```toml
id = "uniform"
depth = "design"

[source]
path = "retention_bench/gain_curve.py"
symbol = "run_reset_sweep"
```

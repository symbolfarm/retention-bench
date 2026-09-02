# Exclude a collapsed learnable band

*ε is relative to r_max*

## Summary

The absolute exclusion threshold is 5% of the task's achievable run-mean
reward. When C − P is smaller, normalised retention is undefined.

## Why

Dividing by a tiny estimated band turns noise into confident-looking ratios.

## What it buys

Honest EXCLUDED results for systems that learned nothing or already saturated
the task.

## Trade-off

Exclusion removes a normalised comparison; raw P, C, R and chance must remain
visible.

## Leads to

band_epsilon · GainCurve.excluded

## Source

```toml
id = "epsilon"
depth = "implementation"

[source]
path = "retention_bench/scoring.py"
symbol = "band_epsilon"
```

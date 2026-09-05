---
status: live
tags: [retrieval, composition, llm, reset, measurement]
tasks: [RB-19]
command: "set -a; source .env; set +a; .venv/bin/python suts/agentic_retrieval/snapshot_runner.py --output snapshots/2026-09-06-agentic-retrieval/measurement.json"
verdict: supports
---

# RB-19 Agentic retrieval on two-hop composition

## Hypothesis

An agent that retrieves the object-to-attribute fact and then uses that result to
retrieve the attribute-to-bin rule will close the widened task's two-hop
composition gap when its store survives a hard process reset.

## Setup

Commit `c3818ac`; `deepseek/deepseek-v4-flash-0731`, temperature 0; default
16-attribute × 2-object symbolic schedule (112 instances per arm); one no-reset
ceiling, one wipe-every-instance prior, and one hard process reset at the
train/probe boundary (instance 48). One run per arm, with 1,000-replicate
per-instance bootstrap CIs. The final run's raw traces are in
[`../../snapshots/2026-09-06-agentic-retrieval/measurement.json`](../../snapshots/2026-09-06-agentic-retrieval/measurement.json).

## Results

| condition | metric | value |
|---|---|---:|
| wiped-store prior | transfer | 0/32 |
| no-reset ceiling | transfer | 32/32 |
| hard reset, store survives | transfer | 32/32 |
| no-reset ceiling | held-out transfer | 16/16 |
| hard reset, store survives | held-out transfer | 16/16 |
| hard reset | normalised retention | 1.033 `[0.803, 1.309]` |
| final run | OpenRouter-reported cost | US$0.014782495432 |

Recall was 29/32 in the ceiling and 31/32 after reset. Four final-run model
replies were malformed (three ceiling, one reset) and scored empty. A retained
32-token pilot had 168/192 malformed replies because hidden reasoning exhausted
the completion budget; it is not capability evidence.

## Verdict

Supports the hypothesis for the **existing two-hop rung**: iterative retrieval
closed it completely, including the held-out split, and the store survived a
real subprocess kill. This rules out two-hop composition as the boundary the
thesis needs. It does not establish semantic consolidation: an external
recording plus query-time composition was sufficient. Deeper hops, revision,
aggregation/absence, and the cost slope over growing history remain open.

The `1.033` normalised score is not evidence that reset helps. The independent
stochastic reset arm happened to score two more recall probes than the ceiling.

## Changelog

- 2026-09-06: created from RB-19.

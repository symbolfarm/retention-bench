# CL-N: A Continual Learning Benchmark for LLM Agents

**Status:** Draft v0.1 — design spec, no implementation yet.

CL-N is a benchmark for evaluating the ability of LLM agents to operate across one or more context-clearing events. A "clear" is defined operationally as a process restart: everything in working memory is gone, and only a designated persistent filesystem survives. The benchmark measures how gracefully a system's task performance degrades as the number of clears (`N`) increases.

The core question CL-N asks: **given an agent's memory scaffolding (or lack thereof), how well does it preserve and reuse task-relevant information across discontinuities?**

## Why this benchmark

Existing memory benchmarks (LoCoMo, LongMemEval, MemoryAgentBench, AMA-Bench, SkillLearnBench, and others) treat sessions as a dialogue abstraction — new turns, simulated time gaps — and mostly measure retrieval quality within a fixed memory architecture. Few evaluate the *number of clears* as a parametric axis, and fewer still offer a clean comparison between:

1. Pure LLMs (no scaffolding) with filesystem access
2. Long-context LLMs attempting to stuff state into a single window
3. Full agent harnesses with explicit memory systems

CL-N fixes the task and varies the clear topology, producing a **retention curve**: performance as a function of N. This reveals degradation shape (linear, stepped, cliff) rather than a single number, and lets systems be compared on equal footing.

## Design at a glance

- **Clear primitive:** process restart. Only the persistent filesystem survives.
- **Memory primitive:** a persistent filesystem at a designated path. The agent designer chooses what lives there and how it is organised.
- **Task structure:** staged DAGs. Stage `k` may depend on outputs of stages `1..k-1`. Clears happen between stages (or more, depending on `N`).
- **Baseline mode:** CL-0 — the whole task runs in one uninterrupted session. This is the no-restart upper bound, not a "short-input" case.
- **Core metric:** the retention curve — task score as a function of `N`, reported alongside resource usage (tokens, filesystem size).
- **Default awareness:** clear-aware (the agent knows clears are coming and how many). Clear-blind is supported as a stiffer variant.

## Document index

- [`protocol.md`](./protocol.md) — the CL-N protocol: clears, stages, run semantics
- [`interface.md`](./interface.md) — the system-under-test contract
- [`metrics.md`](./metrics.md) — retention curves, resource metrics, reporting
- [`tasks.md`](./tasks.md) — task track specifications (book-episodic, codebase; others flagged)
- [`topology.md`](./topology.md) — clear-topology design space and parameters
- [`validity.md`](./validity.md) — contamination, confounds, and guardrails
- [`extensions.md`](./extensions.md) — deferred items: weight-update CL, multi-agent, etc.
- [`open-questions.md`](./open-questions.md) — explicitly unresolved items

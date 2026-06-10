# Extensions

Things deliberately deferred from v1. Each is a coherent extension that fits the CL-N protocol but would expand scope unhealthily if shipped together.

## Weight-update / catastrophic-forgetting CL

The CL-N protocol generalises naturally to weight updates: a "discontinuity" is any event after which the system's state has changed in a way that could lose information. Context clears are one kind; weight updates are another.

A future track could:

- Define a "weight-update event" as the analogue of a clear.
- Replace the persistent filesystem with the model weights themselves (and optionally a replay buffer).
- Test whether training procedures (replay, EWC, LoRA stacking, constructive growth) preserve old capability while learning new tasks.

The metric (retention curve) and the staged DAG structure both port directly. What changes is the SUT — instead of an agent harness, it is a training procedure plus a base model. The interface differs: input is training data plus task data, output is updated weights plus task performance.

This is particularly interesting for constructive-network research, where the system architecture itself is changing across discontinuities. CL-N's weight-update extension would give a clean comparative framing for "does my growing network preserve old capability."

Reasons to defer:
- The machinery is different enough that v1 would be poorly served by trying to do both.
- Weight-update CL has its own well-developed benchmark tradition (continual fine-tuning suites, lifelong learning evals); CL-N adds value here only if it integrates cleanly, not if it duplicates.
- The interface contract would need to be re-specified for training procedures.

## Failure-mode diagnostics

Beyond a score, telling you *why* a system failed:

- Memory-not-stored
- Memory-stored-but-not-retrieved
- Memory-retrieved-but-misapplied
- Memory-corrupted-across-clears

This requires task questions explicitly designed to probe each failure mode and a scoring pipeline that classifies failures rather than just counts them. It significantly improves the diagnostic value of the benchmark for memory-system designers but is a substantial extra piece of work.

Defer to v1.1. v1 should at least ensure question design does not preclude this — i.e., questions should be diverse enough that failure-mode classification is *possible* even if not yet implemented.

## Multi-agent CL

Two or more agents collaborating, where some or all have memory systems, and clears apply to one or more of them. Tests whether collaborative state can be reconstructed when one agent restarts. Relevant to deployment scenarios with agent teams (and to your AgentBand work).

Fits the protocol but adds substantial complexity (orchestration, who-talks-to-whom, scoring fairness). Defer.

## Shared-memory and team-memory variants

Where multiple SUTs share a memory profile (e.g., a team's coding agents share architectural knowledge), CL-N could test whether the shared memory survives clears affecting individual agents and whether knowledge transfers. Particularly relevant given recent industry direction (Cloudflare's Agent Memory, similar offerings).

Defer; treat as a v2 track.

## Cross-task transfer post-clear

Currently CL-N tests whether information from earlier stages of *the same task* survives clears. A natural extension: does information from a *previous task* (different topic, different goal) survive into a new task? This is closer to lifelong-learning territory.

Worth exploring but is conceptually distinct from the within-task retention question. Probably belongs in a sibling benchmark rather than as a CL-N extension.

## Adversarial memory perturbations

Beyond clears, the harness could simulate disk corruption, partial filesystem loss, or memory poisoning (e.g., via prompt injection that writes adversarial content to memory). Tests robustness, which is a legitimate concern given the privacy-leak literature on memory systems.

Out of scope for v1; relevant for safety-focused extensions.

## Determinism and replay tooling

Not strictly an extension — more an implementation property — but worth tracking here. A high-quality reference implementation of CL-N would support deterministic replay of runs given a seed and a recorded trace, enabling post-hoc analysis and debugging of memory systems. The protocol does not mandate this, but the reference implementation should aspire to it.

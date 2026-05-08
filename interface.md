# System-Under-Test Interface

The SUT is treated as a black box. The benchmark does not care what is inside: which model, which memory architecture, which tools, how retrieval works. It cares only about what crosses the boundary.

This document specifies the minimum contract. Anything above it is free to vary.

## Design principle

Keep the interface small. Everything that must be locked down now is listed here. Everything else is deferred to implementation and can be refined without breaking the protocol.

## Inputs the SUT receives

At the start of each session, the SUT receives:

- **Task prompt:** the input for the stage(s) being run this session. Includes any explicit dependencies on artifacts from earlier stages (e.g., "you produced a summary in stage 1; it is available at `./memory/stage1-summary.md`" — though whether and how this pointer is provided is itself an interesting design question; see below).
- **Action budget:** a per-session limit. Expressed as a cap on some combination of tokens, tool calls, or wall-clock time. Tasks specify the units and limits.
- **Persistent filesystem path:** a single directory the SUT can read from and write to. This is the only state that survives clears.
- **Clear schedule (if clear-aware):** a description of when clears will occur in the remainder of the task. May be precise ("clear after this session") or coarse ("2 more clears remain"). Tasks specify the granularity.
- **Awareness flag:** whether this run is clear-aware or clear-blind. This is communicated to the SUT so it can behave accordingly; clear-blind runs simply omit the clear schedule.

## Outputs the SUT produces

Per session, the SUT produces:

- **Stage outputs:** the artifacts each stage requires. Form depends on the task (text answers, patches, structured data, etc.).
- **Any side effects in the persistent filesystem.** These are not "outputs" in the scoring sense but are preserved and snapshotted.

## Externally observed (benchmark harness measures)

The benchmark harness records, without SUT cooperation:

- **Tokens in / tokens out**, per session and cumulative across the run.
- **Wall-clock time**, per session and cumulative.
- **Tool calls**, count and (where available) type breakdown.
- **Filesystem size** at the end of each session.
- **Filesystem delta**: bytes added, bytes modified, bytes removed since the start of the session.
- **Filesystem access patterns** (optional but encouraged): how many files were read, how many written, read-before-write ratios.

## Externally controlled (benchmark harness imposes)

- **When clears happen.** The SUT does not decide this. The harness terminates the process and re-launches it.
- **What survives a clear.** Only the designated filesystem path. Everything else is destroyed.
- **Action budget enforcement.** The harness stops the SUT when the budget is exhausted, even mid-action.
- **Task prompt delivery.** The harness injects prompts into the SUT at the start of each session.

## The six-thing contract

To summarise, the locked-down interface is:

| | What |
|---|---|
| **Inputs** | task prompt, action budget, filesystem path, clear schedule (if aware), awareness flag |
| **Outputs** | stage outputs, filesystem side effects |
| **Observed** | tokens, time, tool calls, filesystem size and delta |
| **Controlled** | clears, persistence boundary, budget, prompt delivery |

Everything else — how the SUT organises its filesystem, whether it uses a vector store or plain markdown or a SQLite database or a git repo, what tools it invokes internally, how it chunks or retrieves — is out of scope for the interface and in scope for the science.

## Modes

A "mode" is a class of SUT defined by what it does with the filesystem. Three modes are specified in v1. All three use the same interface; they differ only in internal architecture.

- **Pure LLM:** an LLM with filesystem read/write tools and nothing else. No harness-level memory scaffolding, no retrieval system, no indexing. The LLM decides what to write, what to read, when to read it. This is the "does the model figure it out" test.
- **Notes mode:** an LLM with filesystem access plus a minimal, specified notes convention (e.g., "write to `./notes.md`, read from it on restart"). A thin, standardised scaffold. Tests whether trivial scaffolding is enough.
- **Full harness:** any agent-plus-memory system — vector stores, knowledge graphs, hierarchical memory, whatever the designer wants. Tests the actual state of the art.

These modes are not exhaustive; they are reference points. Any SUT that conforms to the interface can be evaluated; the modes exist to give comparison anchors.

## Open interface questions (non-blocking for v1)

- **How stage dependencies are surfaced to later sessions.** Option A: the harness passes an explicit pointer ("stage 1 artifact is at path X"). Option B: the harness says nothing and the SUT must find it in its own filesystem. Option B is purer but may be too punishing for weak memory scaffolds. Option A is more realistic. The spec should probably allow both, with tasks declaring which they use.
- **Whether the SUT is told `N` precisely or as a range.** Precise `N` may allow gaming (writing exactly enough to survive exactly that many restarts). A range is more realistic. Default to precise for v1 simplicity; flag as a dimension.
- **Whether the SUT sees its own resource usage.** Allowing this enables budget-aware self-regulation, which is realistic; forbidding it keeps the test cleaner. Default to not visible in v1; flag.

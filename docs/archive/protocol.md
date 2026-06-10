# Protocol

## Vocabulary

- **SUT** (system under test): the full agent being evaluated. Treated as a black box. May be a pure LLM with filesystem access, an LLM with a notes buffer, or a complete agent harness with a sophisticated memory system. The SUT boundary is defined by the interface contract (see [`interface.md`](./interface.md)), not by internal architecture.
- **Task**: a staged DAG of work. Each stage has an input prompt, an action budget, and a set of scorable outputs. Stage `k` may depend on the outputs of stages `1..k-1`.
- **Stage**: one unit of work within a task. Runs in a single session (between clears). Produces outputs that may be scored immediately and/or used as input to later stages.
- **Clear**: a process restart. Working memory is destroyed. Only the persistent filesystem survives.
- **Session**: the period of SUT execution between two clears (or between task start and the first clear, or between the last clear and task end).
- **`N`**: the number of clears in a run. A task with `S` stages can be run at any `N` where the clears are legally placeable. `N = 0` is always legal and is the no-restart baseline. Between-stage clears give `N ∈ {0, 1, ..., S-1}` at minimum; mid-stage clears (an adversarial variant) can extend `N` further.
- **Run**: one execution of one task at one value of `N` by one SUT.
- **Clear-aware / clear-blind**: whether the SUT is told in advance that clears will occur and how many. Clear-aware is the default; clear-blind is a supported variant.

## Clear semantics

A clear is a **process restart**. Operationally:

- All in-memory state of the SUT is destroyed.
- Any in-memory caches, open connections, loaded models-in-process (where applicable), conversation history, and working scratchpads are gone.
- The only thing that survives is the designated persistent filesystem (see [`interface.md`](./interface.md)).
- On the next session, the SUT starts cold. It is re-launched with its initial configuration plus read/write access to the same filesystem path.
- For API-based harnesses that cannot literally restart a process, the equivalent is: fresh conversation, fresh system prompt, all context discarded; filesystem persists. Implementations must document how they realise this equivalence.

Process restart was chosen deliberately over softer alternatives (summarisation, compaction, partial wipes). It is unambiguous, maps to real operational events (crashes, redeploys, cold starts), makes the filesystem the sole persistence channel, and makes cold-start cost a first-class measurable thing.

## Task structure

Tasks are staged DAGs. Formally, a task is a tuple:

- A set of stages `{s_1, ..., s_S}`.
- A dependency relation: for each stage `s_k`, the subset of earlier stages whose outputs it requires as input.
- Per-stage action budgets and input prompts.
- A scoring function (may be per-stage, whole-task, or both).
- Metadata: permissible clear positions, information-density notes for clear-topology design, contamination notes.

Staging is the mechanism that makes CL-N meaningful. A single-stage task with clears inside it tests only intra-task memory under restart; a multi-stage task with between-stage clears tests whether information from earlier stages can be preserved and used later. The staged DAG formalism gives us explicit control over what depends on what.

### Example staging pattern

A three-stage "pyramid" task:

- **Stage 1:** broad exposure. The agent ingests a large body of information and performs some immediate task over it. Produces a stage-1 artifact (e.g., notes, answers, index).
- **Stage 2:** depends on stage 1. The agent is given new information and a task that requires stage-1 context to solve well. Produces a stage-2 artifact.
- **Stage 3:** depends on stages 1 and 2. The agent synthesises across both prior stages, typically requiring information that did not obviously look important in stage 1.

The pyramid structure is the default shape but not the only one. Other shapes (linear chain, wide fan-in, revisitation) are valid and useful.

## Run execution

For a task with stages `s_1, ..., s_S` and a clear schedule at `N`:

1. **Initialise:** the SUT is launched for the first time. The persistent filesystem is empty (or contains only explicitly specified seed state). If clear-aware, the SUT is told the full clear schedule.
2. **Session loop:** for each session:
   a. Run the stages assigned to this session in order, respecting per-stage action budgets.
   b. Collect stage outputs for scoring.
   c. Record resource usage (tokens in/out, wall time, tool calls, filesystem size and delta).
   d. If another session follows, apply a clear.
3. **Clear:** the SUT process is terminated. The persistent filesystem is snapshot (for later inspection). A new SUT process is launched for the next session, pointed at the same filesystem.
4. **Terminate:** after the final stage, collect all outputs and compute task-level scores.

### CL-0 is not trivial

CL-0 means the SUT runs all stages in a single session with no restarts. It is the upper-bound baseline against which higher-`N` runs are compared. It is not a short-input or easy case — the total task may still be large and the SUT must manage its own context across stages. CL-0 is what the retention curve is normalised against.

### Permissible clear positions

Tasks specify where clears are legal. The minimum granularity is between stages. Mid-stage clears are an adversarial variant; tasks that support them must declare it explicitly and specify what mid-stage state-snapshots look like. The default for v1 task tracks is between-stage clears only.

## Awareness variants

- **Clear-aware (default):** at the start of the task (and optionally at the start of each session), the SUT is told how many clears remain and, where meaningful, when they will occur. This tests deliberate memory curation: the SUT can choose to write things to the filesystem in anticipation.
- **Clear-blind:** the SUT is not informed about clears. It experiences each session as though it might be the only one. This tests whether memory systems do the right thing by default — whether they capture potentially-useful information without being told it will be needed.

Clear-aware is the default because it gives a cleaner signal about memory-system design capability; clear-blind is the stiffer real-world test and should be supported as an opt-in mode.

## What a run produces

A single run yields:

- Per-stage scores.
- Whole-task score.
- Per-session resource traces (tokens, tool calls, wall time, filesystem size/delta).
- Filesystem snapshots at each clear.
- A full trace of SUT actions (for post-hoc analysis and ideally replay).

The trace format should support replay and diagnostic analysis (see [`open-questions.md`](./open-questions.md) on determinism).

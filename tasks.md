# Task Tracks

Two primary tracks in v1:

1. **Book-episodic memory** — reading a long novel or non-fiction work across sessions and answering questions that require cross-session synthesis.
2. **Large codebase tasks** — multi-phase work against a substantial codebase, where later phases depend on understanding built in earlier phases.

Additional track candidates are listed at the end as "future tracks" — they are well-formed ideas that could be added to v1.1 or v2 without changing the protocol.

Each track in this document specifies the structure and scoring approach but defers specific asset selection (which books, which repos) to a separate curation pass. Asset selection is non-trivial work with contamination implications; see [`validity.md`](./validity.md).

---

## Track 1: Book-episodic memory

### Rationale

Books are natural staged input: chapters provide clean stage boundaries, information accumulates over the work, and questions can probe everything from surface facts to thematic synthesis. The track tests fine-grained factual persistence, entity tracking, temporal reasoning, and thematic accumulation — all core to episodic memory.

### Structure

A book is partitioned into stages. Each stage corresponds to a contiguous span (typically a chapter or small group of chapters). Clears happen between stages.

- **Stage `k` input:** the text of that span of the book, plus a stage-specific task (a set of questions, a summary request, or both).
- **Stage `k` output:** answers to stage-specific questions and/or a requested summary artifact.
- **Dependency structure:** late-stage questions draw on information from many earlier stages. Final-stage questions are the highest-value — they require synthesis across the whole book.

### Question taxonomy

Questions within and across stages should be drawn from a taxonomy similar to LongMemEval's, adapted for this track:

- **Surface factual:** single facts from a specific stage ("what colour was the house in chapter 3?").
- **Entity tracking:** state of an entity over time ("by chapter 10, what has happened to character X?").
- **Multi-hop:** facts that require joining information from two or more stages.
- **Thematic / causal:** why did an event happen, what motif appeared across chapters, what does the work argue.
- **Retroactively relevant:** facts that were incidental when introduced but become important later. These stress whether memory systems capture broadly or narrowly.

### Scoring

Per-question scoring: exact match for atomic facts, rubric-based LLM-as-judge for open-ended answers (with inter-judge variance reported), structural metrics for summaries. Stage scores aggregate question scores; the task score aggregates stage scores with higher weight on later stages (since they test more of the memory system).

### No-re-reads is the default

The filesystem may contain notes, indexes, or summaries the SUT has written — but **the original book text must not be present** after the stage in which it was provided. Tasks enforce this: the input text is injected at stage start and is not available from the filesystem. Whatever the SUT wants to preserve, it must paraphrase or restructure into its own artifacts.

This is deliberate. Allowing the raw text to persist lets a lazy SUT just cache the book and re-read relevant sections, which confounds the memory signal. Forcing paraphrase-or-lose-it tests whether the memory system captured what *would be* needed.

### Contamination

Books in the pretraining corpus are a serious problem. Mitigations:

- Prefer recent or obscure works.
- Prefer works where questions can be answered *only* from the reading trajectory (e.g., "what did you note about X in stage 2?" rather than "what happens on page 50?").
- For a portion of the track, use procedurally generated or human-authored novel texts. These lose literary richness but are contamination-proof.
- Report contamination-likelihood alongside each asset.

See [`validity.md`](./validity.md) for the broader discussion.

---

## Track 2: Large codebase tasks

### Rationale

Codebases stress procedural memory (how the code fits together), decision memory (why things are done this way), and skill accumulation (we already solved a similar bug). They are also where the benefit of memory scaffolding is most visible in real-world agent deployments, which makes this track ecologically valid.

### Structure

A sequence of work phases against a fixed codebase. Each phase is a stage. Clears happen between phases.

Example phase structure:

- **Stage 1: orientation.** Agent is given a goal (e.g., "implement feature X" or "fix bug Y") and must build understanding of the relevant parts of the codebase. Produces an orientation artifact (notes, diagrams, an index).
- **Stage 2: first attempt.** Agent produces a candidate change (patch, PR, test additions). Evaluated by running tests and/or rubric.
- **Stage 3: revision.** Simulated reviewer feedback is provided. Agent must revise. Requires remembering decisions made in stage 2 and rationale from stage 1.
- **Stage 4 (optional): extension.** A new but related task is introduced, requiring the agent to reuse understanding built earlier.

### Scoring

- **Automated:** do the tests pass? Does the code build? Does the patch apply cleanly?
- **Rubric:** does the solution match codebase conventions? Is it minimal? Does it avoid obvious mistakes the agent had already learned to avoid?
- **Efficiency:** cumulative tokens and tool calls across the run. A memory system that requires re-scanning the whole repo after every clear pays a visible cost here.

### No-re-reads flag

Default: **graded.** After a clear, the agent may not re-read files it had already accessed before the clear. It may read files it had not touched yet. This mirrors realistic behaviour — an agent that has already "learned" a file should not need to re-read it if its memory system did its job.

Stricter variant: **no re-reads of any file accessed in any earlier session.** Cumulatively more punishing; tests deeper compression.

Looser variant (for comparison runs): **free re-reads.** The task is trivially solvable by re-scanning; this variant exists to show how much memory buys you over re-derivation.

All three variants should be runnable from the same task definition, toggled by a flag.

### Contamination

Popular public repos are in pretraining data. Mitigations:

- Prefer private repos (with owner cooperation).
- Prefer recent or niche repos.
- Modify public repos: rename symbols, reorganise files, introduce synthetic complications. The version the SUT sees is not the version in pretraining.
- Use procedurally generated codebases for a portion of the track (reduced realism, contamination-proof).

---

## Future tracks (deferred)

These are well-formed ideas. They would fit the CL-N protocol with no changes. Not in v1 because we want to ship with two tracks done well rather than four done poorly.

- **Scientific paper stack.** A sequence of related papers read across sessions. Tests synthesis across the stack, noticing contradictions/refinements. Naturally aligned with research-workflow use cases.
- **Iterated debugging of a stateful system.** Agent debugs a system that evolves across sessions. Tests maintaining a mental model of a moving target.
- **Teach-then-use.** Pre-clear, agent is taught an idiosyncratic DSL, convention, or procedure. Post-clear, must apply it to novel inputs. Pure test of procedural memory that resists re-derivation.
- **Multi-session planning with revealed information.** Agent pursues a long-range goal, information is revealed gradually across sessions, final plan requires cross-session synthesis. Good stress test for prioritisation — memory systems that hoard indiscriminately will fail this.
- **Procedurally-generated world exploration.** Agent explores a simulated environment across sessions; clears force it to build a persistent world model. Clean control of information density and contamination-proof.

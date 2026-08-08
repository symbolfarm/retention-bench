# Task Tracks

Two primary tracks in v1:

1. **Book-episodic memory** — reading a long novel or non-fiction work across sessions and answering questions that require cross-session synthesis.
2. **Large codebase tasks** — multi-phase work against a substantial codebase, where later phases depend on understanding built in earlier phases.

Additional track candidates are listed at the end as "future tracks" — they are well-formed ideas that could be added to v1.1 or v2 without changing the protocol.

Each track in this document specifies the structure and scoring approach but defers specific asset selection (which books, which repos) to a separate curation pass. Asset selection is non-trivial work with contamination implications; see [`validity.md`](./validity.md).

---

## Track 1: Book-episodic memory

### Rationale

Books are natural staged input: chapters partition cleanly, information accumulates over the work, and questions can probe everything from surface facts to thematic synthesis. The track tests fine-grained factual persistence, entity tracking, temporal reasoning, and thematic accumulation — all core to episodic memory.

### Structure (atomic-event model, locked Turn 5 of [[design-dialogue]])

A run is a sequence of **events** of three types:

- `READ(material)` — the harness delivers a span of book text (typically a chapter or small group of chapters) via `STAGE_INPUT`. `STAGE_META.type = read`. The SUT updates its state however it likes; `STAGE_OUTPUT` is empty or a trivial ack.
- `QUIZ(questions, probe)` — the harness delivers a question set via `STAGE_INPUT`. `STAGE_META.type = quiz`, `STAGE_META.probe ∈ {prior, ceiling, retention}`. The SUT writes answers to `STAGE_OUTPUT`.
- `RESET` — between events: the harness kills the SUT process, snapshots the persistent directory, and spawns a fresh process. Only `DIR` survives.

A **SUT process** spans the events between two `RESET`s. Within a process the SUT's in-context state, working memory, and (for constructive SUTs) live weight updates persist across multiple `READ`s and `QUIZ`s; the `RESET` is the only event that destroys non-`DIR` state.

#### Probe semantics

For each scored question `q` about reading material `m`, three probes can be issued:

- **`prior`**: a `QUIZ` containing `q` issued *before* any `READ` covering `m`. Measures what the SUT already knows from pretraining or earlier exposure. The score `P(q)` is the prior-knowledge baseline.
- **`ceiling`**: a `QUIZ` containing `q` issued *after* `READ(m)` and *before* the next `RESET`, within the same SUT process. Measures what the SUT can answer with `m` still accessible in its working state. The score `C(q)` is the capability ceiling.
- **`retention`**: a `QUIZ` containing `q` issued *after* at least one `RESET` following `READ(m)`. Measures what survives. The score `R(k, q)` is parameterised by `k`, the number of `RESET`s separating the relevant `READ` from the `QUIZ`.

The cross-reset-purity rule (Agreed #10 of [[design-dialogue]]) requires: **no scored retention question is answerable from the current `STAGE_INPUT` alone.** Operationally, every retention `QUIZ` is separated from the relevant `READ` by ≥1 `RESET`.

#### Example run shape

For a 10-chapter book with a sample event sequence:

```
QUIZ(Q_A, prior)              ← prior on ch. A
READ(ch_A)
QUIZ(Q_A, ceiling)            ← ceiling on ch. A
RESET
QUIZ(Q_A, retention@1)        ← R(1) on ch. A
READ(ch_B)
READ(ch_C)
QUIZ(Q_{A,B,C}, mixed)        ← retention on A, B, C at different k
RESET
QUIZ(Q_A, retention@2)        ← R(2) on ch. A
...
```

A `mixed` `QUIZ` contains questions tagged individually as `prior`, `ceiling`, or `retention@k` per the rules above. The harness aggregates per-tag.

### Question taxonomy

Question categories (drawn from a LongMemEval-style taxonomy, adapted):

- **Surface factual:** single facts from one chapter.
- **Entity tracking:** state of an entity over time.
- **Multi-hop:** facts requiring information from two or more chapters.
- **Thematic / causal:** why events happen, motifs across chapters, what the work argues.
- **Retroactively relevant:** facts that were incidental when introduced but become important later. Stresses whether memory systems capture broadly or narrowly.

Each question has a `probe` tag (`prior` / `ceiling` / `retention@k`) determining when it is issued. The taxonomy is orthogonal to the probe structure: any taxonomy category can be probed at any of the three probes.

### Scoring

Per question, the eval retains up to three scalars: `P(q)`, `C(q)`, `R(k, q)` for one or more `k`. Per-question scoring uses exact match for atomic facts, rubric-based LLM-as-judge for open-ended answers (with inter-judge variance reported), and structural metrics for summaries.

The headline aggregation is **normalized retention**:

```
normalized_retention(k, q) = (R(k, q) − P(q)) / max(C(q) − P(q), ε)
```

— with an `ε` floor to handle questions where `C(q) ≈ P(q)` (the SUT couldn't answer even with the text, or already knew without it; in either case the question carries no usable signal at this SUT and is reported but not aggregated).

Aggregation across questions and across `k` produces the retention curve (see [`metrics.md`](../metrics.md)). Higher-weight aggregation on later-stage retroactively-relevant and thematic questions remains the default.

### Cross-reset purity (the load-bearing constraint)

The eval is built on the principle that **scored retention questions must require state carried across at least one `RESET`**. Concretely:

- The original book text must not be present in `DIR` after the `READ` event that delivered it. The harness deletes `STAGE_INPUT` and `STAGE_META` between every event (Agreed #12 of [[design-dialogue]]).
- A retention `QUIZ` for material `m` is never issued in the same SUT process as `READ(m)`. At least one `RESET` separates them.
- The SUT may copy text into its own files during a `READ` event, and those files persist across `RESET`s (this is the memory system doing its job). The strict variant of [`extensions.md`](./extensions.md) forbids verbatim copies; the default permits them but resource metrics make the storage cost visible.

Allowing the raw text to persist trivially lets a lazy SUT just cache the book and re-read relevant sections, which confounds the memory signal. Forcing the SUT to paraphrase, index, or otherwise transform — or, for constructive SUTs, to encode into weights — tests whether the memory system captured what *would be* needed.

### Contamination

With the `prior` probe in place, contamination is **measured rather than avoided** (see [`validity.md`](./validity.md), Confound 1). A book that the SUT has effectively memorised from pretraining will show high `P(q)`; the eval reports `R − P` and isn't fooled. This widens the usable asset pool considerably.

Asset-selection optimisations remain useful, not required:

- Prefer recent works for lower baseline `P`.
- Prefer trajectory-specific questions ("what did you note about X?") where applicable.
- For a portion of the track, use AI-written or procedurally generated texts to span the contamination spectrum and cross-validate the contamination correction.
- Report contamination-likelihood alongside each asset for transparency.

---

## Track 2: Large codebase tasks

> **Note (Turn 5, 2026-05-13):** The Track 2 description below reflects the v0.1 stage-and-clear framing. The atomic-event model (`READ` / `QUIZ` / `RESET`) and three-probe baselines locked in Turn 5 of [[design-dialogue]] apply here too in principle, but mapping them onto interactive code work (orientation → patch → revise) is non-trivial — the natural unit is closer to a `WORK` event than a passive `READ`. A full rework of this section is deferred until after the book-track is shaken out end-to-end.

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

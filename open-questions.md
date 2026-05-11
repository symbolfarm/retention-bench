# Open Questions

Items the spec has deliberately not resolved. Listed here so they are not lost and so the project can prioritise them. Roughly ordered by how blocking each is for a working v1.

> **Re-triage 2026-05-11.** Items below have been re-read under the
> Turn 3 agnostic five-thing interface (`STAGE_INPUT` → SUT → `STAGE_OUTPUT`
> + persistent-state directory + action budget + optional clear schedule/awareness).
> Items 1 and 4 were reframed by that resolution; others survive as-written.
> See [[design-dialogue]] Turn 3 for the agreements driving this.

## Blocking for v1 implementation

**1. Stage-dependency surfacing convention.** Under the agnostic interface, what does `STAGE_INPUT` say about what's already in the persistent-state directory at stage start? Two candidate conventions:
- *Explicit pointer:* `STAGE_INPUT` enumerates the artifacts the SUT wrote last stage (e.g. "your stage-1 notes are at `./notes.md`").
- *Implicit:* `STAGE_INPUT` says nothing; the SUT must discover the directory's contents itself.

The spec previously said "allow both, declare per task." A v1 default needs to be picked. Probably explicit-pointer for agent-area SUTs (removes a filesystem-discovery confound) and irrelevant for SUTs whose persistent state is a single fixed filename like `checkpoint.pt` — so likely "explicit when there's ambiguity, silent otherwise."

**2. Determinism requirements.** Should runs be deterministic given a seed? LLM stochasticity makes full determinism hard, but recording-and-replay of the SUT's trace is feasible. The reference implementation should commit to a trace format. The spec should commit to "runs must be replayable for analysis," but the *level* of determinism is open.

**3. Tracing format.** Connected to the above. What does a CL-N run trace look like on disk? Needs to capture: prompts in, actions out, tool calls, tokens, filesystem snapshots, scores. Likely JSON-lines plus filesystem tarballs per snapshot. Worth standardising before tasks are written.

**4. Reference SUT implementations.** Per Turn 3 Agreed #7, reference modes live above the interface and proliferate (notes-LLM, vector-store, SGD fine-tune, EWC, constructive-growth, no-state baseline, …) rather than being fixed at "pure LLM / notes / full harness." For shake-out, v1 needs at least one runnable reference SUT per **area of focus** — minimally a notes-LLM (agent-memory area) and a constructive-net or naive-checkpoint baseline (constructive area). A no-state baseline in each area is also wanted so the retention curve has a meaningful zero. These do not have to be SOTA; they have to be runnable and produce sensible scores at CL-0. The full reference-mode catalogue is its own design pass (Turn 4 candidate option 3).

## Important but non-blocking

**5. Range vs. precise `N` in clear-aware mode.** The spec defaults to telling the SUT precise `N`. A range would be more realistic. Probably worth supporting both eventually; v1 picks one.

**6. SUT visibility into its own resource usage.** Default in v1 is "not visible." But realistic agents track their own token spend. A future variant could expose this. Flag.

**7. Scoring rubrics for open-ended outputs.** Both v1 tracks (book and codebase) have open-ended scoring components. LLM-as-judge is the default plan but introduces variance and bias concerns. Need to commit to a rubric format and an inter-judge agreement protocol.

**8. Asset curation pipeline.** Tracks specify structure, not specific books or repos. Curation is non-trivial: contamination assessment, modification (where applicable), question authoring, validation that questions are answerable from the trajectory but not from pretraining. This is its own work-stream.

**9. Procedural generation pipelines.** For the synthetic portions of each track (and for the procedurally-generated future tracks), a generation pipeline is needed. Out of scope for spec but on the implementation roadmap.

## Worth noting, low priority

**10. Leaderboard / public reporting infrastructure.** If CL-N is published, how are results reported? Public leaderboard? Per-paper reporting? This is a release concern, not a design concern. Defer.

**11. Cost-aware scoring.** Whether to include some explicit cost-quality combined score. Currently the spec says "report both, do not collapse." Some users will want a single number anyway. Possibly add a Pareto-frontier visualisation; do not change the headline metric.

**12. Versioning policy.** When tasks are updated (questions revised, assets swapped), how are scores comparable across versions? Standard benchmarks deal with this via versioned task suites. Defer; relevant when v1.1 ships.

**13. License and access for assets.** Books, code, papers all have licensing implications. Curation needs to address this. Practical, not theoretical, but worth flagging early.

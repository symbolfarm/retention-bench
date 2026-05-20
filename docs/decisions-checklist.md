---
title: Pre-implementation decisions checklist
project: retention-bench (continual-learning-eval)
status: resolved — all hard-blockers locked 2026-05-20; soft-blockers + new decisions resolved same session
tags: [checklist, decisions, scoping]
---

# Pre-implementation decisions checklist

Decisions to lock before coding the first runnable book-track task. Each item lists 2–3 options and a recommendation. Options are starting points; reframings welcome.

Origin: discussion 2026-05-17 (Claude review of the v0.1 spec set, post-Turn-6). See `../AGENTS.md` for context.

---

## Hard blockers (lock before any code)

### 1. Trace / record format

- **A.** JSONL event stream + per-`RESET` tarball snapshot, single run directory.
- **B.** SQLite database for events + tarball snapshots.
- **C.** OpenTelemetry-style structured logs.

**Recommend: A.** Plain text, greppable, trivially shipped and re-ingested. Tarballs preserve `DIR` provenance for post-hoc forensics. SQLite is a derivation away if querying gets painful; OTel is overkill for a single-process harness.

**Toby**: Agreed - A.

### 2. `STAGE_INPUT` internal structure

- **A.** Tagged sections in a single string: `<TEXT>…</TEXT>`, `<QUESTIONS>…</QUESTIONS>`, `<META>…</META>`. (Turn 4 PENDING proposal.)
- **B.** Structured JSON with named fields, SUT parses.
- **C.** Multiple files dropped in a per-stage input directory.

**Recommend: A.** LLM-native, regex-parseable, SUTs ignore tags they don't care about. JSON forces a parse step before any LLM sees content; multi-file is heavier and asymmetric with `STAGE_OUTPUT`.

**Toby**: Agreed - A.

### 3. `C` (capability ceiling) operational definition

- **A.** Text in context + prior in-process `QUIZ` history retained. (Toby's intent, clarified 2026-05-17.)
- **B.** Text in context, no prior `QUIZ` history.
- **C.** Two ceilings reported (`C_isolated`, `C_accumulated`).

**Recommend: A**, written into `metrics.md` as "capability ceiling under same-process accumulation." Real agents accumulate Q&A state; the ceiling should reflect that. B is artificial; C doubles probe cost for marginal analytic value.

**Toby**: Agreed - A.

### 4. Verbatim-caching default (cross-reset purity strictness)

- **A.** Permissive: SUT may persist verbatim spans of `READ` text into `DIR`. Storage cost reported.
- **B.** Strict: no verbatim spans of `READ` text in `DIR`. Permissive available as labelled variant.
- **C.** Always run both, report both curves.

**Recommend: B.** Permissive turns retention into retrieval-over-cache, which dominates the headline curve while measuring the least architecturally interesting thing. Strict default is what makes the eval test *compression*. C is rigorous but doubles every cohort run.

**Toby**: Agreed - B; however, I'm not interested in designing the harness to enforce this. I think this SUT developers should self-report if their run was strict or permissive on verbatim records.

### 5. Question-author confound strategy

- **A.** Rotate question-author models across the cohort (different model per novella).
- **B.** Single question-author held constant + bias-audit subset re-written by a second author.
- **C.** Multi-author per novella (every novella gets two question sets).

**Recommend: A.** Cheapest and cleanest. The novellas already vary on form/tone/setting; varying question-author across them folds question-style variance into the same axis. C is more rigorous but doubles question-authoring work for marginal gain at this stage.

**Toby**: Agreed - A.

### 6. Per-question scoring approach

- **A.** Per-question-type scorers: exact-match for surface facts; rubric LLM-as-judge for entity arcs / multi-hop / retro; multi-judge for thematic synthesis (variance reported).
- **B.** Single rubric LLM-as-judge for everything.
- **C.** Defer entirely to an existing library (DeepEval `GEval` / Inspect scorers); pick per question type from its catalogue.

**Recommend: A, implemented via C where possible.** Surface facts shouldn't go through LLM judgment (waste of variance budget); thematic synthesis needs multi-judge. Reuse existing scorer implementations rather than reinvent. The harness emits a per-`QUIZ` record file (`(question, probe, k, sut_answer, gold, type)`); scoring is a pure function over that file, swappable later.

**Toby**: Agreed - A+C combination.

### 7. Stage-dependency surfacing default

- **A.** Always explicit pointer ("your earlier work is at `./notes.md`, `./summary.md`").
- **B.** Always silent (SUT discovers `DIR` itself).
- **C.** Per-task field, default explicit.

**Recommend: C with default A.** Removes filesystem-discovery as a confound for v1's first tasks; per-task override available for tasks that specifically want to test discovery. B is purer but punishing for weak scaffolds and conflates two things we want to measure separately.

**Toby**: **Let's discuss**, I'm not sure that I want to require the SUT to be agentic. I'd prefer tasks to simulate tool calls in the input context so that non-agentic models are still able to task the test. Some of the expected quiz responses might be tool-call-like, but these shouldn't be expected to be executed to answer problems. I'd like to discuss this before making a call.

**Resolved 2026-05-20 — option D (reframing):** original A/B/C question collapses. The test harness is thin: sandbox + text I/O + `DIR` existence/snapshotting + reset. It does *not* interpret SUT-emitted directives. Agentic SUTs run their own scaffold internally and handle tool calls themselves. Non-agentic SUTs get *parallel variants* of tasks where mock tool-call transcripts are baked into `STAGE_INPUT` directly. Results reported as **two leaderboards** (agentic / in-context), side-by-side, not averaged. `DIR` semantics: agentic variant owns its `DIR` contents; non-agentic variant has no `DIR` to snapshot (mock transcript replaces it). Mock-transcript authorship strategy deferred (hand-authored vs. reference-agent-generated vs. frontier-model-generated) — flag as a soft decision for cohort-1 prep.

### 8. `DIR` accounting (filesystem-size metric)

- **A.** Uncompressed bytes on disk + file count.
- **B.** `tar.gz` size after each snapshot.
- **C.** Both reported.

**Recommend: C.** Uncompressed bytes is operational reality; compressed size catches "wrote 1 GB of redundant text" pathologies. Both are essentially free to compute.

**Toby**: Agreed - C.

### 9. Action budget units for v1

- **A.** Tokens (in + out, summed) per session.
- **B.** Wall-clock time per session.
- **C.** Tuple `(tokens, tool calls, wall time)` — first to exhaust ends session.

**Recommend: A** for the budget itself; report tool calls and wall time alongside but don't budget on them. Tokens are the most portable unit across SUT architectures (LLM-only, constructive, RAG). Wall time penalises slow local hardware. Tool-call counts are architecture-dependent.

**Toby**: Agreed - A, with reporting on wall-clock. I'm not sure about tool-calls. That sounds like having to peek inside the harness, or is that mostly just counting the number of API calls?

**Resolved 2026-05-20:** A for the budget; wall-clock reported alongside. Tool-call counting is harness-external in both SUT modes — for agentic SUTs it's the count of API/model invocations observable at the SUT boundary; for non-agentic SUTs there are none. No harness peek required. Reported as "harness-observed side-effect count" when meaningful, omitted otherwise.

### 10. `question_seen_before` provenance tracking

- **A.** Boolean per `(question, R-probe)` record.
- **B.** Integer count of prior exposures (`P`, `C`, earlier `R(k')` for `k' < k`).
- **C.** Both — boolean plus full list of prior probe instances with timestamps.

**Recommend: B.** Most flexible for post-hoc analysis without bloating the schema. Boolean loses info when a question is probed at multiple `R(k)` values; full list is over-engineering for analysis that just needs a count.

**Toby**: Agreed - B.

---

## Soft blockers (needed soon; can be drafted in parallel)

### 11. Reference SUT specs (initial set)

- **A.** No-state baseline + notes-LLM (minimal).
- **B.** No-state + notes-LLM + naive-RAG (verbatim chunks + embedding retrieval).
- **C.** Just no-state for harness validation; defer notes-LLM to first real cohort.

**Recommend: B.** Naive-RAG is "the thing to beat" — having it as a reference makes any new memory architecture's value immediately legible. All three are cheap to implement and together span the interesting baseline frontier.

**Toby**: Agreed - B.

### 12. Replayability minimum

- **A.** Trace is sufficient to reconstruct *what the SUT did*; not bit-for-bit deterministic.
- **B.** Seeded determinism required (temperature=0 + seed); same trace must reproduce same SUT actions.
- **C.** Full record-and-replay: re-running from trace produces identical SUT outputs.

**Recommend: A.** LLM determinism is partial at best across providers and over time; demanding it constrains SUT design unnecessarily. Trace-as-record is enough for analysis and audit.

**Toby**: Agreed - A.

### 13. Asset acceptance procedure (cohort-1 review)

- **A.** Solo Toby reviews each novella + memory-targets.
- **B.** Validator tool (checks floors, source-anchor strings exist verbatim in novella, IDs unique) + Toby for prose.
- **C.** B plus a second LLM contamination spot-check; Toby final sign-off.

**Recommend: B + C.** Tool catches structural failures cheaply; second model handles contamination/style spot-checks; Toby's attention goes only to genuinely human-judgment calls.

---

**Toby**: Sounds good - B + C.

---

## New decisions (added + resolved 2026-05-20)

### 14. Constructive SUT weight accounting

Where do model weights live for constructive SUTs (growth in attention/embeddings/MLPs of a pre-trained base), and what counts toward the storage metric?

- **A.** Full checkpoint in `DIR` every reset.
- **B.** Delta-only in `DIR`; pre-trained base lives outside `DIR` as SUT "code."
- **C.** Both reported: delta as headline storage metric, total footprint (base + delta) as deployer-cost auxiliary.

**Resolved: C, with B as the load-bearing definition.** Principle: `DIR` contains what the agent *produced in response to the book*, not the machinery it used. Consistent with notes-LLM (notes in `DIR`, base model not counted) and naive-RAG (vector index in `DIR`, embedding model not counted).

**Delta definition rule (covers in-place training):** if the serialised checkpoint doesn't change size, storage delta = 0. SUTs that do continued / test-time training adapting the whole network in place legitimately report zero storage delta — *but* compute cost (FLOPs, see #15) is then the load-bearing comparable metric and is scrutinised.

**Murky cases self-declared:** for LoRA-style adapters or in-place fine-tuning, the SUT developer declares what counts as delta. Verification rule: `delta + frozen base` must reproduce the loaded model bit-for-bit. Same trust+audit model as verbatim-caching (#4).

**Toby:** Agreed - C with careful delta definition; in-place training → storage delta = 0, FLOPs carries the cost signal.

### 15. FLOPs reporting

How are train-FLOPs and inference-FLOPs collected for SUTs (essential the moment #14's "in-place training → storage delta = 0" rule is in play)?

- **A.** Self-report by developer per stage. Trust + audit.
- **B.** Harness records wall-clock + developer declares hardware tier (`gpu_model`, `count`). Envelope cross-check via wall-clock × declared peak FLOPs.
- **C.** Framework-instrumented (PyTorch FLOP counters wrapped around forward/backward).

**Resolved: A + B as cross-check.** Self-reported FLOPs is the headline number; wall-clock × declared hardware is the sanity envelope. Mismatches flagged in audit. C not required — too much developer burden, breaks for non-PyTorch SUTs.

**API-only SUT carve-out:** hosted models accessed via HTTP report `(tokens_in, tokens_out, model_id, api_call_count)` instead of FLOPs. Trace schema accommodates both regimes from day one.

**Toby:** Agreed - A + B.

### 16. Execution environment & hardware tiers

How is the eval run, and how are SUTs grouped for leaderboard comparability?

- **A.** Container only; developer brings any hardware; wall-clock recorded, rest self-declared. Fully open.
- **B.** Container + reference hardware tiers; developer reports which tier. Within-tier comparable, cross-tier caveated.
- **C.** Centralised execution on hosted cluster (developers submit container + weights).

**Resolved: B.** Ship the harness as a Docker image with a `run.sh` entrypoint. Execution stays with the developer. Reproducibility appendix in trace format: `(hardware_tier, declared_gpu, declared_train_flops, declared_inference_flops, wall_clock)`. C is out of scope for a research benchmark without dedicated infra funding.

**Tier set (locked):**

| Tier | Spec |
|---|---|
| Consumer | Single consumer GPU, ≤32 GB VRAM, declared model (covers 3090/4090/5090, also AMD/Mac equivalents) |
| 1×H100 | Single H100 80GB (smallest serious cloud unit; Lambda etc.) |
| 8×H100 | 8×H100 80GB node |
| API | Hosted model via HTTP; declared `model_id` |
| Open | Anything else — TPU, AMD, Apple Silicon, multi-node, custom. Stands alone, not cross-compared. |

**Design note:** consumer tier is the tier where hardware most tightly constrains model size and therefore where retention-as-architecture matters most. Protocol must remain accessible at the consumer tier — do not implicitly design for 8×H100.

**Toby:** Agreed - five tiers as above.

### 17. Train / no-train leaderboard lane — DEFERRED

Whether to split the leaderboard further on whether SUTs perform in-place training between stages (no-train: storage delta is the *only* retention mechanism vs. open: in-place training allowed, FLOPs scrutinised). Combined with agentic/non-agentic split from #7 this would be a 2×2.

**Status:** deferred. Revisit after first cohort produces data; may turn out to be unnecessary if FLOPs scrutiny in #15 + storage rule in #14 are sufficient to keep the comparison honest.

---

## Minimum-viable set

If only a subset can be locked before coding starts: **1, 2, 3, 4, 6, 9, 11.** Defaults for the rest can be applied and revisited once the first run produces data.

**Status 2026-05-20:** all 16 active decisions resolved (#17 deferred). Cleared to start MVP harness implementation.

## Framework split (architectural decision underlying the above)

Confirmed direction (2026-05-17): **custom harness for the protocol (event loop, process kill, `DIR` lifecycle, probe bookkeeping); existing library (DeepEval / Inspect / lm-eval) for per-question scoring.** The harness emits a standard per-`QUIZ` records file; scoring is a pure function over it and the library is swappable.

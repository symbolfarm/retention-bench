# Related work: StudyBench / "Machine Studying"

> Li, Battle & Khattab (MIT CSAIL / Broadcom), *Machine Studying*, June 2026.
> <https://jacobxli.com/blog/2026/machine-studying/>

A concurrent benchmark project with a strong shared thesis and a **mostly
orthogonal measurement axis**. This note records the overlap, what is
leverageable, and where Retention Bench stays net-new — so the relationship is
legible for outreach and so we don't accidentally re-derive their framing under a
different name.

## What StudyBench is

*Machine Studying* asks: given **only a corpus** `C` (a codebase, a manual, a
literature) and **no downstream task, reward, or QA pairs**, can an agent
autonomously develop *expertise* in that domain before it knows anything about
the eventual exam? Crucially, the corpus stays available at test time — studying
is supposed to make test-time use *more efficient*, not to memorise the corpus
into the weights.

- **Expertise** is defined as the weighted area under the agent's
  performance-vs-**inference-compute** curve (WAUC), discounting expensive
  budgets. An agent that only gets accurate after enormous search has *low*
  expertise.
- **Studying intelligence** = how efficiently an agent converts *study* compute
  into expertise.
- **Three tasks**: Studying-DSPy (stale-knowledge control), Studying-OpenClaw
  (post-cutoff, novel-from-scratch), Studying-Literature (~50k papers, far
  beyond any context window). Agents are a model in a ReAct harness with
  `grep`/`glob`/`read_file`, run at four inference budgets (direct, k=5, k=20,
  k=20-forced).
- **Three studying paradigms** surveyed: (1) self-supervised weight updates
  (continual pre-training / next-token prediction, LoRA); (2) synthetic data
  (synthetic SFT, on-policy distillation, eventually self-generated RL); (3)
  amortized context management (a "cheatsheet" the agent writes itself).
- **Headline empirical result**: naive weight updates (CPT, synthetic SFT)
  *underperformed* the base model — "memorization is no substitute for
  expertise." Only the cheatsheet developed noticeable expertise, and only at
  low budgets. On the literature task they separate *reach* (did the right
  evidence ever get retrieved = search) from *recall@100* (did the agent choose
  to keep it = expertise).

## Shared thesis (the conceptual overlap)

Both projects independently argue that "continual learning" as commonly
discussed (on-the-job improvement, catastrophic forgetting over a task stream,
context management) **misses the real problem**, and both pick essentially the
same real problem:

| Shared idea | StudyBench | Retention Bench |
|---|---|---|
| Existing CL framings are under-specified; we need a crisp goal + benchmark | coins *Machine Studying*, expertise = WAUC | reset-axis retention curve; CL-Bench's `mean_gain` is "one number at one implicit reset density" |
| **Understanding/expertise ≠ memorization/stenography** is THE signal | §7 "Memorization is no substitute for expertise"; the "cramming" curve | memorization-vs-**transfer** probe split in `symbolic_associative_retention`; "understanding vs stenography" in the constructive-SUT brief |
| Headline metric = (normalised) area under a curve | expertise = WAUC over compute | AURC / normalised retention `(R−P)/(C−P)` over `k` |
| **Material novelty is a validity requirement, not variety** | corpora chosen by training cutoff; DSPy "stale knowledge is a dangerous state" | `metrics.md` "prior saturation and material novelty"; keep mean `P` low, rising `P` = asset aging out. The curriculum task sidesteps this entirely by using **nonce symbols** with no world-knowledge prior |
| Reject "the corpus disappears at test time" | corpus stays available; studying makes use efficient | survive-dir persists; mechanism-agnostic SUT contract |

The novelty/validity convergence is the most striking: StudyBench reaches it by
hand-picking post-cutoff corpora and running a same-capability/different-cutoff
model pair (GPT-5.1 vs GPT-5.4-mini) to isolate "studying" from "capability."
Retention Bench's curriculum task reaches the same end by construction — nonce
symbols (`norb is red`) have no prior, so `P` is structurally low and `C − P` is
guaranteed open.

## The key difference: orthogonal axes

The two benchmarks measure orthogonal axes of the *same* surface — performance as
a function of **(study / state survived)** × **(inference compute spent)**:

- **StudyBench fixes studying, sweeps inference compute** → expertise (WAUC).
- **Retention Bench fixes inference, sweeps hard resets `k`** (and, via RB-3,
  training-exposure count) → retention / sample-efficiency curves.

Neither measures the other's axis, so they compose rather than compete. Two
further divergences:

- **Open-book vs. closed-after-erasure.** StudyBench is open-book at all times.
  Retention Bench's hard RESET (`SIGKILL` + respawn, only the survive-dir
  persists) is *closed-book unless the system externalised what it learned*. We
  test survival of learning across erasure of working state — a regime StudyBench
  deliberately excludes.
- **Scale.** StudyBench targets frontier agents on real, large corpora; the
  current Retention Bench direction is **tiny models (≈TinyStories scale) on
  synthetic curricula**. The tasks are not interchangeable — a TinyStories-scale
  model cannot study 50k ML papers — but the *conceptual apparatus* and metrics
  transfer cleanly.

## Their three paradigms ≈ our reference SUTs

StudyBench's §6 taxonomy maps almost one-to-one onto our SUT classes:

| StudyBench paradigm | Their instantiation | Our reference SUT |
|---|---|---|
| Self-supervised weight updates | CPT / next-token prediction over corpus (LoRA) | **`constructive`** — byte-level NTP gradient steps on read text, *plus* capacity growth |
| Synthetic data / environments | synthetic SFT + on-policy distillation | *(none yet — gap)* |
| Amortized context management | self-written "cheatsheet" | **`notes_llm`** (cumulative notes to `DIR`) |
| Structured / keyless memory & baseline | base model + ReAct search | **`bsm_accumulator`**, **`associative_memory`** (keyless state), and the retired no-state floor |

Two observations:

1. **Their CPT bet is our `constructive` SUT** — with the one variable they did
   *not* test: **growing capacity** (function-preserving Net2Net-style growth)
   rather than fixed-capacity LoRA. The constructive-growth cell is the
   unexplored corner of *their own* taxonomy.
2. Their **cheatsheet ≈ our `notes_llm`**, and it was their *strongest* studier.
   That sets the bar our constructive SUT must clear: not "beat the base model"
   but "beat verbatim context management on the **transfer** probe," where a
   notepad of past instances only partly helps.

## How the tiny-model + curriculum plan changes the picture

The pivot to tiny models and a synthetic memorization/transfer curriculum:

- **Strengthens the conceptual alignment.** Our `symbolic_associative_retention`
  task is a clean, small-scale instantiation of "memorization is no substitute
  for expertise": the `memorization` probe (recall `norb`'s colour) is the
  verbatim/stenography axis; the `transfer` probe (recombine colour→bin) is the
  understanding axis. StudyBench argues this distinction at frontier scale; we
  can exhibit it deterministically and cheaply.
- **Reframes "studying intelligence" as sample efficiency.** StudyBench plots
  expertise vs *study compute*. RB-3's repeated-exposure variant plots
  recall/transfer vs *number of training exposures* — the same "efficiency of
  acquiring expertise" idea, measured in exposures rather than tokens. Worth
  stating this correspondence explicitly when RB-3 lands.
- **Weakens the "borrow their corpora" option.** DSPy/OpenClaw/Literature are
  large and presuppose a competent base model (their studier, Qwen3.5-9B, "writes
  good PyTorch"). They are not runnable substrates for a TinyStories-scale model.
  We borrow the *framing and metrics*, not the corpora.
- **Reinforces the transfer-probe-as-headline choice.** Their cheatsheet result
  warns that verbatim caching is a stubbornly strong baseline. On nonce-symbol
  curricula a keyless accumulator will trivially ace *memorization* probes, so
  the *transfer* probe is the only honest discriminator — exactly why the task
  reports `transfer_mean_reward` separately and `bsm_accumulator`/`associative_memory`
  exist as the verbatim-memory baselines to beat.

## What stays net-new for Retention Bench

- **Hard RESET / `k`-axis** — absent from StudyBench; they never erase working
  state.
- **Constructive capacity growth** — the untested cell in their own taxonomy, and
  the project's central bet (new knowledge lands in new parameters → less drift
  on old ones).
- **Concept-drift reset placement** (on-vs-off-boundary, the non-monotonic story)
  — no analog in StudyBench.
- **Storage/compute accounting across erasure** (cold-start tokens, survive-dir
  growth trajectory) — they report per-budget token counts but have no
  survive-dir / storage axis.

## Leverage opportunities

Ranked for the current (tiny-model, curriculum) direction:

1. **Adopt an "expertise (WAUC)" reporting column**, reconciled the same way we
   reconciled with CL-Bench's `mean_gain`. Reporting retention at more than one
   inference budget would place us on the same 2-D surface as StudyBench and make
   the two directly composable.
2. **Borrow `reach` vs `recall@100`** as the template for our shallow-recall vs
   deep-adaptation decomposition: "was the signal available?" vs "did the system
   use it?" maps onto memorization-available vs transfer-applied.
3. **Add a synthetic-SFT reference SUT** to fill the one missing paradigm cell,
   so we can reproduce the "cramming" curve shape on our reset/exposure axes.
4. **Steal the cutoff-pair validity probe** (same-capability / different-cutoff
   models) if/when we add any natural-language corpus task, as an external check
   that `C − P` measures studying rather than capability.

## Positioning note

This is a high-profile group — **Omar Khattab is the DSPy author**, and
StudyBench uses DSPy as a corpus. Two implications:

- **Frame Retention Bench as complementary**, not a competing definition of the
  problem: *expertise under state-erasure*, and *retention/sample-efficiency*
  rather than inference-compute expertise. The reconciliation we already did with
  CL-Bench's `mean_gain` is the template; an "expertise (WAUC)" column does the
  same for StudyBench.
- **The constructive-growth cell being the gap in their taxonomy** is a natural
  collaboration / outreach hook (see `.tasks/C5-author-outreach.md`).

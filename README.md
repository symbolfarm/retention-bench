# retention-bench

[![CI](https://github.com/symbolfarm/retention-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/symbolfarm/retention-bench/actions/workflows/ci.yml)

A research workbench and instrument for measuring what a system learned during a
run, i.e., continual learning. Two topics of interest are:

- **Learning that survives a discontinuity that erases working state**
- **Learning that is integrated and not merely stored**

"Bench" here means **workbench**, not benchmark. This is the instrument a
research programme uses and shares publicly, so that its design can be inspected
and pointed at other systems. See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the
research agenda, and [Scope and limits](#scope-and-limits) below.

retention-bench is an **extension on top of [Continual Learning Bench](https://github.com/pgasawa/continual-learning-bench)**
(CL-Bench; Asawa et al., arXiv:2606.05661, Apache-2.0). It adopts CL-Bench's
runner, task interface, and evaluation contract, and points them at a different
question, using:

- **A hard RESET** — a process-kill discontinuity across which *only* an on-disk
  survive-directory persists. A system under test (SUT) is a subprocess spanning
  one reset to the next, so scoring evaluates learning survival or retention.
- **Mechanism-agnostic memory** — the SUT interface (read a stage, optionally
  mutate the survive-dir, write a response) does not distinguish between memory
  implemented with fine-tuning, structural growth, notes, and/or retrieval.

There are three main reasons to use performance across hard resets:

1. Realism: in real-world agentic systems, agents are regularly reset or have
   their context cleared. Being able to resume or continue tasks across resets
   is an important agent capability.
2. Memory: hard resets motivate exploration and innovation of persistent and
   efficient memory mechanisms. This workbench is agnostic to memory mechanism,
   but aims to quantify performance and cost trade-offs. Reloading everything
   from disk on each reset is a legitimate strategy; the reset only makes its
   recurring cost visible rather than amortised across a run.
3. Horizon: some job and task types require integrating and abstracting information
   over a very large number of episodes. This workbench aims to build to tasks
   that demonstrate long-term episodic and semantic learning.

## The claim it exists to test

> Continual learning agents need expanding memory: episodic memory growing
> across sessions; semantic memory growing across episodes.

First, experiences must survive discontinuities that erase working state. Second,
experiences must be abstracted so the system ends up knowing things no single
episode contains.

A distinction that does the work is between a **recording** and a **memory**.
A recording is verbatim, retrieved unchanged, and complete. A memory has been
re-represented — stored in a form other than the one it arrived in — which is
why it composes. Lossiness is a frequent symptom of that rather than the
definition of it, and re-representing is not the same as compressing: a growing
semantic index restructures without shrinking at all.
Global attention composes over the whole window, and a model shown instances of
a rule can induce it and apply it to an input it never saw. That is abstraction
within an episode, and it is what transformers are best at.

What are the limits and trade-offs to in-context learning (ICL) and efficient long
context? What are the limits to recordings and retrieval for abstracting across
episodes? Contexts are transient and ICL may have structural limitations in
compositional depth of abstraction. Retrieval from recordings is necessarily
selective and a system cannot abstract over what it did not retrieve.
Agentic harnesses with frontier models that effectively manage context and 
retrieval may not have easily discernible limitations.

The suspicion behind this workbench is that most agent memory today is recording
rather than memory: stored verbatim, retrieved selectively, and re-derived from
scratch each session. We would rather find out than assume it. A motivation for
developing the workbench is to investigate constructive or growing neural
networks as an approach to growing episodic and semantic memory — work that
happens in `constructive-retention`, a sibling project by the same author that
is not yet public. **No such learner ships in this repository**; it reaches the
harness through the same documented process contract a third party would use,
and the validity hazard that creates is discussed under
[Scope and limits](#scope-and-limits). The mechanism-agnostic interface lets
agents, memory systems, and novel learning algorithms be compared on the same
footing.

The probe ladder in this workbench is being designed to evaluate episodic and 
semantic memory capabilities of agents and memory systems. A probe ladder that can
be passed with a simple memory store could indicate the claim is false or that the
probe ladder is deficient. The two are distinguishable by what the probe asks
for: a store passing a probe whose answer sits inside a single stored item means
the rung was too easy, while a store passing probes whose answers are properties
of the whole set is evidence against the claim.

## Quickstart

Requires **Python 3.13+** (the `cl-benchmark` dependency sets this floor).

```bash
# 1. Install (editable):
pip install -e .

# 2. Reinstall the cl-benchmark pin *editable* — required, not optional. As a
#    wheel it silently drops the task data files its tasks load at runtime and
#    every task construction fails. Keep the SHA in sync with pyproject.toml.
pip install -e "git+https://github.com/pgasawa/continual-learning-bench.git@9cc63c0f429048b843e8d43ac4f2b0ea4df13724#egg=cl-benchmark"

# 3. Run the canonical end-to-end smoke test (offline, no API key):
./run.sh smoke
```

Use `pip` for step 2 specifically, even if you manage the rest of the
environment with `uv`: `uv pip install -e` rejects a git URL outright
("Editable must refer to a local directory"), and a non-editable install fails
at runtime for the reason in the comment. `uv pip install pip` into the venv,
then run step 2 with `python -m pip`.

This drives the **keyless `bsm-accumulator`** reference SUT through CL-Bench's
`blind_spectrum_monitoring` task on the gain-curve sweep, printing the
`P` / `C` / `R(k)` retention table. It runs **offline with no API key and no
model weights** — the accumulator just unions every spectrum peak it has seen
into the survive-dir — so the smoke proves the full reset/retention pipeline
end-to-end without network or credentials.

The reset axis is swept by `--reset-every`; each arm gets a fresh survive-dir.
The prior arm `P` (survive-dir wiped on every reset) is the stateless floor, the
ceiling `C` (no reset) is the best the system can do, and `R(k)` shows how
retention holds as `k` hard resets accumulate. See
[`suts/bsm_accumulator/README.md`](suts/bsm_accumulator/README.md).

To see what the metric discriminates, run the keyless **reference ladder** — the
chance / floor / graded / capacity-limited / full-retention SUTs on one task,
offline:

```bash
./run.sh ladder
```

Normalised retention separates the stateless floor from full retainers, places a
geometrically-forgetting rung strictly between them, and sits every rung against
a measured chance line. The run is deterministic, so a clean checkout reproduces
the committed numbers exactly; those numbers and their interpretation are in
[`docs/reference-ladder.md`](docs/reference-ladder.md).

For an arbitrary CL-Bench task / SUT, the gain-curve driver is SUT-agnostic:

```bash
python -m retention_bench.gain_curve --list-tasks
python -m retention_bench.gain_curve --task <task> --sut "<launch command>" \
  --extra-pythonpath <sut-dir> --reset-every 1 --reset-every 2
```

The native task's width and length are knobs, and chance level is
`1/num_attributes` — see
[`docs/associative-curriculum.md`](docs/associative-curriculum.md).

(LLM-backed reference SUTs like `notes_llm` need an OpenAI-compatible endpoint —
copy `.env.example` to `.env` and set `OPENROUTER_API_KEY`.)

The uniform `--reset-every k` sweep measures **graceful degradation** across
repeated erasure. To instead ask *did capability migrate into the weights* — reset
**once** at the train/probe boundary with `--reset-at`, removing the store — see
[`docs/phased-store-removal.md`](docs/phased-store-removal.md). These answer
different questions; see [How retention is scored](#how-retention-is-scored) for
which to pick.

### Bring your own task

You don't have to register a task in this repo to run it. `--task-spec` imports a
`ContinualLearningTask` subclass dynamically, by dotted module path or `.py` file
path, so a task can live in the SUT's own repo:

```bash
python -m retention_bench.gain_curve \
  --task-spec /path/to/my_repo/my_task.py:MyTask \
  --sut "<launch command>" --reset-every 1 --reset-every 2
```

The task is imported and run in the **harness** interpreter (not the SUT
subprocess), so keep BYO task files dependency-light — pydantic/stdlib, no torch.

## How retention is scored

Each CL-Bench instance is scored by the task's own reward; we run three kinds of
arm from a fresh survive-dir: `P` (prior — stateless, survive-dir wiped every
reset), `C` (ceiling — no reset, state accumulates unbroken), and `R(k)`
(retention after `k` hard resets). The metric is **normalised
retention** `(R − P) / (C − P)` — how much of the *learnable band* survived the
resets. A band where `C ≈ P` (nothing was learnable, or priors already saturate)
is excluded rather than scored. Full definitions, the reset axis, and
reconciliation with CL-Bench's gain are in [`docs/metrics.md`](docs/metrics.md).

**Two questions, two drivers — pick by the claim you are making.** There is no
single headline number. The uniform `--reset-every k` sweep measures *graceful
degradation* under repeated erasure; phased store removal (`--reset-at`) asks
whether capability **migrated** into what persisted, which is the question the
claim above is about. Using the wrong one inverts verdicts — the *same SUT* can
score `1.000` phased and `0.000` uniform. Why, and which to reach for, is in
[`docs/phased-store-removal.md`](docs/phased-store-removal.md).

The keyless reference ladder is currently calibrated on the uniform sweep only; a
phased ladder does not exist yet.

## Scope and limits

What this instrument is ultimately *for* is detecting a system that acquires
genuinely new competence during a run. This includes competence that corrects
something it previously held and applies it to inputs it has never seen, in
domains where the answer can be checked. Recall under resets is the bottom rung,
not the goal; see [`docs/ROADMAP.md`](docs/ROADMAP.md) §"What would count as
success". Against that aim, this is an early-stage instrument, and it is worth
being explicit about what that means:

- **One owned task.** The native curriculum is
  `symbolic_associative_retention` — deterministic nonce-symbol associations with
  recall and two-hop composition probes, including a never-bridged held-out
  split. CL-Bench's own tasks run through the same seam, but the probe families
  on the roadmap (aggregation, revision, application) do not exist yet.
- **Co-designed with the system expected to do well on it.** retention-bench is
  developed alongside `constructive-retention` — a research project on
  unreleased gradient-free constructive learning, by the same author. This is a
  genuine validity hazard. To mitigate this, we are publishing the probe design
  and thesis (in [`docs/ROADMAP.md`](docs/ROADMAP.md)) *before* those systems
  are measured through the instrument, so the design is timestamped ahead of any
  favourable result.
- **No language model has been measured yet.** As of this release the ladder
  covers keyless synthetic reference systems only. The central claim above is
  therefore unfalsified in either direction; the first real LLM measurement is
  the immediate next step.
- **Cost is not settled.** Cost matters (less than accuracy) but token counts are
  not architecture-neutral (a constructive system spends zero), so no cost metric
  is published as authoritative. See the roadmap's *Exploring* tier.
- **All published results are the authors' own**, produced by the commands in
  this README. The keyless ladder is deterministic and reproducible from a clean
  checkout; anything model-dependent will be dated and pinned separately.

Adoption, if it comes, should follow an interesting result rather than benchmark
infrastructure. We would rather be told the instrument is measuring the wrong
thing now than after we have published results on it.

## Documentation

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — the research agenda: what we think we
  are measuring, the probe ladder, and the open questions. Published before the
  measurements exist.
- [`docs/`](docs/) — the reference docs. Start with
  [`docs/sut-interface.md`](docs/sut-interface.md) (the SUT process contract) and
  [`docs/metrics.md`](docs/metrics.md) (how retention is scored);
  [`docs/README.md`](docs/README.md) is the full index and repo tour.

## Authorship

The research direction, the claim under test, and the design decisions in this
repository are Toby Lightheart's. Much of the prose — including these docs — and
a substantial share of the code were drafted or revised in collaboration with
Claude (Anthropic), working as an assistant across many sessions. The
`Co-Authored-By` trailers in the git history record this commit by commit; this
note states it plainly rather than leaving it to be inferred.

## License

Apache-2.0 — see [`LICENSE`](LICENSE). retention-bench builds on Continual
Learning Bench (Apache-2.0), consumed as a pinned-commit dependency; attribution
is in [`NOTICE`](NOTICE).

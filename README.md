# retention-bench

A research instrument for measuring whether what a system learned during a run
**survives a discontinuity that erases working state** — and whether what
survives is *integrated* or merely *stored*.

"Bench" here means **workbench**, not benchmark. There is no leaderboard and no
submission process: this is the instrument a research programme uses and shares
publicly, so that its design can be inspected and pointed at other systems. See
[`docs/ROADMAP.md`](docs/ROADMAP.md) for the research agenda, and
[Scope and limits](#scope-and-limits) below for what it does *not* yet do.

retention-bench is an **extension on top of [Continual Learning Bench](https://github.com/pgasawa/continual-learning-bench)**
(CL-Bench; Asawa et al., arXiv:2606.05661, Apache-2.0). It adopts CL-Bench's
runner, task interface, and evaluation contract, and contributes the two things
CL-Bench explicitly lacks:

- **A hard RESET** — a process-kill discontinuity across which *only* an on-disk
  survive-directory persists. A system under test (SUT) is a subprocess spanning
  one reset to the next; everything in memory is gone at each reset, so any score
  that survives must have been carried through the survive-dir.
- **A constructive / parametric system class** — a train-and-grow reference
  learner that grows capacity across reads, with compute accounting, alongside
  the agent-memory reference SUTs.

## The claim it exists to test

> Continual learning agents need expanding memory: episodic memory growing
> across sessions; semantic memory growing across episodes.

Two levels, and they are not the same requirement. The first asks that
experience survive a discontinuity that erases working state. The second asks
that it be abstracted — that the system end up knowing things no single episode
contains.

The first is cheap: write to disk. The second is what this instrument measures.

The distinction that does the work is between a **recording** and a **memory**.
A recording is verbatim, retrieved unchanged, and complete. It answers any
question whose answer sits inside a single stored item, and nothing else. A
memory has been compressed into a structure — which is why it composes, and why
it is lossy. Compression is not a defect here; it is what forces structure, and
a store under no pressure to compress never acquires any.

This is **not** a claim that transformers cannot abstract. Within a context
window they plainly do: attention composes over the whole window, and a model
shown instances of a rule can induce it and apply it to an input it never saw.
That is abstraction over episodes, and it is what transformers are best at.

The claim is about where that abstraction *goes*. It is computed at query time
and discarded with the process; what persists is the token sequence that
produced it. The store is a recording and the abstraction is transient, so the
next session re-derives it from scratch — and re-derives it over whatever subset
was retrieved, not over the whole history. That last part is structural:
retrieval selects by query, so a system cannot abstract over what it did not
retrieve, and questions whose answers are properties of the entire set have no
query that surfaces them.

This can be shown false, and the falsification is cheap to state: a system that
clears the probe ladder with nothing but a store.

## Why a hard RESET

The obvious objection is that longer context windows make this moot. They do
not, because of what the reset does.

A long-context system can always reload everything from disk when the process
restarts. That is a legitimate strategy and it works. And it costs the full
re-read — and the full re-derivation of whatever it had already worked out —
**every session, forever.**

Without resets, that cost is paid once and amortised across a run, and the
difference between paying-per-session and paying-once is invisible. **The hard
RESET converts a one-time cost into a recurring one**, which is what makes the
difference measurable. The reset is not a handicap applied to retrieval systems;
it is the mechanism that exposes a scaling difference that is otherwise hidden.

Because the SUT interface is **mechanism-agnostic** (read a stage, optionally
mutate the survive-dir, write a response), fine-tuning, structural growth, notes,
and retrieval are all just reference modes above one contract — the harness
cannot tell them apart.

## Quickstart

Requires **Python 3.13+** (the `cl-benchmark` dependency sets this floor).

```bash
# 1. Install (editable):
pip install -e .

# 2. Reinstall the cl-benchmark pin *editable*. This step matters: installed
#    as a wheel (which step 1 does for dependencies), cl-benchmark's packaging
#    silently drops the task data files (templates/variants/schedules) its
#    tasks load at runtime, and every task construction fails. The editable
#    install keeps the full source tree on disk. Keep the SHA in sync with
#    the pin in pyproject.toml.
pip install -e "git+https://github.com/pgasawa/continual-learning-bench.git@9cc63c0f429048b843e8d43ac4f2b0ea4df13724#egg=cl-benchmark"

# 3. Run the canonical end-to-end smoke test (offline, no API key):
./run.sh smoke
```

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

The committed numbers and interpretation are in
[`docs/reference-ladder.md`](docs/reference-ladder.md). On the default
112-instance schedule of `symbolic_associative_retention` (`r_max = 64/112 ≈
0.571`, so `k = 55` and `k = 111` measured resets), normalised retention
separates the stateless floor (`no_state`, `0.000`) from full retainers
(`bounded_memory` and `associative_memory`, both `1.000`) and places a
geometrically-forgetting rung strictly between them (`reset_lossy`, `0.547` at
`k = 55` decaying to `0.344` at `k = 111`). Raw score adds the capacity tier and
places every rung against a measured chance line — analytic chance is
`1/num_attributes = 1/16 = 0.0625` per probe, `0.0357` as a run-mean, and the
`random_guess` rung measures `0.027`.

For an arbitrary CL-Bench task / SUT, the gain-curve driver is SUT-agnostic:

```bash
python -m retention_bench.gain_curve --list-tasks
python -m retention_bench.gain_curve --task <task> --sut "<launch command>" \
  --extra-pythonpath <sut-dir> --reset-every 1 --reset-every 2
```

The width and length of the native task are knobs
(`--task-kwarg num_attributes=16 --task-kwarg objects_per_attribute=2` are the
defaults); chance level is `1/num_attributes`, so widening the attribute set is
how you lower it. See
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
degradation*: how performance holds as erasure accumulates, with state loss
interleaved with learning. It cannot cleanly answer whether capability
**migrated** into what persisted, because resetting mid-learning conflates
"nothing migrated" with "the store wasn't around long enough to learn from" — a
system that consolidates perfectly and one that only reads its store back can both
score low, for opposite reasons. For that question — the one the claim above is
about — use phased store removal (`--reset-at`), which resets once at the
train/probe boundary with the store gone. The difference is not cosmetic: on the
worked example in [`docs/phased-store-removal.md`](docs/phased-store-removal.md)
the *same SUT* scores `1.000` phased and `0.000` uniform.

The keyless reference ladder below is currently calibrated on the uniform sweep
only; a phased ladder does not exist yet.

## Scope and limits

What this instrument is ultimately *for* is detecting a system that acquires
genuinely new competence during a run — including competence that corrects
something it previously held — and applies it to inputs it has never seen, in
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
  developed alongside [constructive-retention](https://github.com/symbolfarm/constructive-retention),
  a research project on gradient-free constructive learning, by the same author.
  That is a genuine validity hazard. We name it rather than hide it, and we
  publish the probe design and thesis (in [`docs/ROADMAP.md`](docs/ROADMAP.md))
  *before* those systems are measured through the instrument, so the design is
  timestamped ahead of any favourable result.
- **No language model has been measured yet.** As of this release the ladder
  covers keyless synthetic reference systems only. The central claim above is
  therefore unfalsified in either direction; the first real LLM measurement is
  the immediate next step.
- **Cost is not settled.** We believe cost matters as much as accuracy, but token
  counts are not architecture-neutral (a constructive system spends zero), so no
  cost metric is published as authoritative. See the roadmap's *Exploring* tier.
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

## License

Apache-2.0 — see [`LICENSE`](LICENSE). retention-bench builds on Continual
Learning Bench (Apache-2.0), consumed as a pinned-commit dependency; attribution
is in [`NOTICE`](NOTICE).

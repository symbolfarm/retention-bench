# retention-bench

A benchmark measuring how gracefully an LLM-agent system's task performance
**degrades across discontinuities that erase working state**. The headline
artifact is a *retention curve*: task score as a function of the number of
resets `k`, comparing systems with different memory / state-preservation
strategies on equal footing.

retention-bench is an **extension on top of [Continual Learning Bench](https://github.com/pgasawa/continual-learning-bench)**
(CL-Bench; Asawa et al., arXiv:2606.05661). It adopts CL-Bench's runner, task
interface, and evaluation contract, and contributes the two things CL-Bench
explicitly lacks:

- **A hard RESET** — a process-kill discontinuity across which *only* an on-disk
  survive-directory persists. A system under test (SUT) is a subprocess spanning
  one reset to the next; everything in memory is gone at each reset, so any score
  that survives must have been carried through the survive-dir.
- **A constructive / parametric system class** — a train-and-grow reference
  learner that grows capacity across reads, with compute accounting, alongside
  the agent-memory reference SUTs. The keyless reference set spans a retention
  *ladder* — `no_state` (in-RAM only; the floor), `reset_lossy` (geometric
  forgetting; the graded `0 < norm < 1` rung), `bounded_memory`
  (FIFO-capped survive-dir), and `associative_memory` / `bsm_accumulator` (full
  persistence) — plus the `notes_llm` cumulative-notes LLM and the `constructive`
  learner. See
  [`docs/reference-ladder.md`](docs/reference-ladder.md).

Because the SUT interface is **mechanism-agnostic** (read a stage, optionally
mutate the survive-dir, write a response), fine-tuning, structural growth,
notes, and retrieval are all just reference modes above one contract — the
harness can't tell them apart.

## Quickstart

Requires **Python 3.13+** (the `cl-benchmark` dependency sets this floor).

```bash
# 1. Install (editable):
pip install -e .

# 2. Run the canonical end-to-end smoke test (offline, no API key):
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
floor / capacity-limited / full-retention SUTs on one task, offline:

```bash
./run.sh ladder
```

The committed numbers and interpretation are in
[`docs/reference-ladder.md`](docs/reference-ladder.md): normalised retention
cleanly separates a non-retainer (floor) from retainers, while raw score adds the
capacity tier.

For an arbitrary CL-Bench task / SUT, the gain-curve driver is SUT-agnostic:

```bash
python -m retention_bench.gain_curve --list-tasks
python -m retention_bench.gain_curve --task <task> --sut "<launch command>" \
  --extra-pythonpath <sut-dir> --reset-every 1 --reset-every 2
```

(LLM-backed reference SUTs like `notes_llm` need an OpenAI-compatible endpoint —
copy `.env.example` to `.env` and set `OPENROUTER_API_KEY`.)

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
(retention after `k` hard resets). The headline metric is **normalised
retention** `(R − P) / (C − P)` — how much of the *learnable band* survived the
resets. A band where `C ≈ P` (nothing was learnable, or priors already saturate)
is excluded rather than scored. Full definitions, the reset axis, and
reconciliation with CL-Bench's gain are in [`docs/metrics.md`](docs/metrics.md).

## Documentation

See [`docs/`](docs/) — start with [`docs/sut-interface.md`](docs/sut-interface.md)
(the SUT process contract) and [`docs/metrics.md`](docs/metrics.md) (how retention
is scored).

## License

Apache-2.0 — see [`LICENSE`](LICENSE). retention-bench builds on Continual
Learning Bench (Apache-2.0), consumed as a pinned-commit dependency; attribution
is in [`NOTICE`](NOTICE).

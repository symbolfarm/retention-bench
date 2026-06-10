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
  the agent-memory reference SUTs (no-state, notes, naive-RAG).

Because the SUT interface is **mechanism-agnostic** (read a stage, optionally
mutate the survive-dir, write a response), fine-tuning, structural growth,
notes, and retrieval are all just reference modes above one contract — the
harness can't tell them apart.

## Quickstart

Requires **Python 3.13+** (the `cl-benchmark` dependency sets this floor).

```bash
# 1. Install (editable), with the no-state reference SUT's dependencies:
pip install -e ".[no-state-sut]"

# 2. Provide an API key for the OpenAI-compatible endpoint (OpenRouter default):
cp .env.example .env
#   then edit .env and set OPENROUTER_API_KEY=...

# 3. Run the canonical end-to-end smoke test:
./run.sh smoke
```

This drives `tasks/smoke-test/task.yaml` (a public-domain text + 5 questions)
through the harness and the **no-state** reference SUT, then scores the trace and
prints a `P` / `C` / `R(k)` retention table. The no-state SUT is the floor row —
it never reads the source — so every question is correctly excluded by the
`C ≈ P` rule (see [`docs/metrics.md`](docs/metrics.md)).

Runs are written to `runs/<run-id>/` (gitignored): `trace.jsonl`,
`questions.jsonl`, run/SUT manifests, the survive-`dir/`, snapshots, stage I/O,
and SUT stderr — the full audit trail.

For an arbitrary task: `./run.sh <task.yaml> --sut <sut-dir>` (or call
`python -m harness ...` and `python -m scorer <run-dir>` directly).

## How retention is scored

Each question is probed three ways: `P` (prior knowledge, before any reading),
`C` (capability ceiling, with the text fresh in the same process), and `R(k)`
(retention after `k` resets). The headline metric is **normalised retention**
`(R − P) / (C − P)` — how much of what was *learnable in principle* survived the
resets. Questions where `C ≈ P` (nothing was learnable, or priors already
saturate) are excluded rather than scored. Full definitions, the reset axis, and
reconciliation with CL-Bench's gain are in [`docs/metrics.md`](docs/metrics.md).

## Documentation

See [`docs/`](docs/) — start with [`docs/sut-interface.md`](docs/sut-interface.md)
(the SUT process contract) and [`docs/metrics.md`](docs/metrics.md) (how retention
is scored). The input/output data contracts are in
[`docs/task-definition-schema.md`](docs/task-definition-schema.md) and
[`docs/trace-schema.md`](docs/trace-schema.md).

## License

Apache-2.0 — see [`LICENSE`](LICENSE). retention-bench builds on Continual
Learning Bench (Apache-2.0), consumed as a pinned-commit dependency; attribution
is in [`NOTICE`](NOTICE).

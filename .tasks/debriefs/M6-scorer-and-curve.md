# Debrief: M6 Exact-match scorer + retention-curve renderer

**Completed:** 2026-05-20
**Commit:** 5c68568

## What shipped

`scorer/` package (5 modules, ~250 LOC) — a pure consumer of the
trace data contract:

- `exact_match.py` — case-/whitespace-/punctuation-insensitive
  exact-match scorer. Normalises via NFKC + lowercase + ASCII/curly
  punct-to-space + whitespace collapse. `parsing_status ∈
  {not_found, ambiguous}` short-circuits to score 0 but is preserved
  for diagnostics.
- `aggregate.py` — `QuestionAggregate` dataclass collects
  `P`, `C`, and `R(k)` per question. `normalised_retention` applies
  `(R−P)/max(C−P, ε)`. `aggregate_curve` mean-aggregates across
  questions per `k`, excluding `C−P < ε` questions per `metrics.md`.
  Default `ε = 0.05`.
- `curve.py` — deterministic stringly-typed table renderer (sorted
  by `question_id`, ascending `k`). Excluded questions are shown
  with `(excluded — C≈P)` in the norm column.
- `__main__.py` — CLI entry point: `python -m scorer <run-dir>`.
  Reads `<run-dir>/questions.jsonl`, prints the table. `--epsilon`
  override flag for experimentation.
- `__init__.py` — re-exports the public surface.

27 new tests under `tests/` covering exact-match edges, C≈P
exclusion, normalised-retention math, multi-`k` aggregation,
parsing-status failures, CLI smoke, and a byte-identical-output
determinism check. Full suite: **40 passed, 1 skipped**.

## Descoped / deferred

- **LLM-judge scoring** — backlog B3.
- **Plot rendering** — printed table only, per brief "Out of scope".
- **Multi-SUT / leaderboard rendering** — post-MVP.
- **Per-question-type weighting** — aggregate is unweighted mean
  per brief.
- **Variance / error bars** — `metrics.md` calls for error bars in
  the reporting format, but with a single seed the curve renders a
  point estimate. Real cohort runs will need this.

## Design decisions

- **Entry point is `python -m scorer <run-dir>`, not
  `python -m scorer <run-dir>/trace.jsonl`.** The brief's
  `trace.jsonl` argument predates the M1 file-split decision
  (`trace.jsonl` = event stream; `questions.jsonl` = scoring
  contract — see `docs/trace-schema.md` line 83). Pre-locked with
  Toby before launch; taking a directory and opening
  `questions.jsonl` internally is cleaner ergonomically and matches
  the "scorer is a pure consumer of the data contract" framing.
- **Input file is `questions.jsonl`, not `trace.jsonl`.** Same
  origin as above. The scorer never opens `trace.jsonl` or stage
  payloads. Pre-locked.
- **Normalisation strategy: NFKC + lowercase + punct→space + WS
  collapse.** More aggressive than the brief's "case-insensitive,
  whitespace-normalised" baseline, but matches the smoke-test
  reality from M5 (LLM answers will arrive with trailing periods,
  curly quotes from JSON-mode outputs, etc.). Conservative enough
  to still distinguish "salesman" from "travelling salesman"
  (tested). Trade-off: an LLM that answers "the travelling
  salesman" against gold "travelling salesman" still misses — we
  do not strip determiners. The format-hint convention from M5
  ("Answer with a single word") is the deliberate counterpart.
- **`parsing_status ∈ {not_found, ambiguous}` scores 0
  unconditionally**, even if a happenstance match would have
  occurred. Faithful read of `docs/trace-schema.md`
  §"SUT-answer ingestion": "The scorer treats `not_found` and
  `ambiguous` as score = 0 but they remain distinguishable in the
  records for diagnostics."
- **Missing `P` or `C` → excluded.** The brief specifies excluding
  `C ≈ P` questions, but says nothing about missing probes. Treated
  as excluded since the formula is undefined without both
  endpoints. Surfaces in `QuestionAggregate.is_excluded()`.
- **Multiple retention scores at the same `k` → mean.** The schema
  permits multiple seeds / re-probes at the same `k`. Used mean
  rather than first-occurrence to match `metrics.md`'s
  "Multiple seeds / trials estimate variance at each (q, k)"
  framing. Single-seed runs (the MVP case) are unaffected.
- **Output is plain ASCII (no Unicode box-drawing).** Brief's
  example table uses `|` separators; stuck with that for greppable
  smoke-test output. Em-dashes only appear inside the "excluded —
  C≈P" tag and as placeholders for missing cells.

## Observations

- **No `scorer/` reference in `pyproject.toml` package discovery.**
  `[tool.setuptools.packages.find]` is `include = ["harness*"]`.
  The scorer still imports fine from a source checkout (pytest puts
  cwd on `sys.path`), and the CLI works via `python -m scorer`, but
  if/when retention-bench is `pip install`-ed, the scorer won't be
  shipped. Flagging — see follow-ups.
- **Brief acceptance criteria #6 lists `python -m scorer
  <run-dir>/trace.jsonl` verbatim, which directly contradicts
  `docs/trace-schema.md` line 83** ("The scorer reads
  `questions.jsonl` exclusively; it never needs to touch
  `trace.jsonl` or stage payloads"). Resolved per pre-lock — this
  is the canonical record of the resolution.
- **The smoke-test fixture (M5) has only 5 questions and a single
  retention probe at `k=1`**, so the aggregate curve will be a
  single point. The scorer renders this correctly (verified via the
  CLI test), but the "curve" framing is more aspirational than
  literal for the MVP smoke run.
- **Determinism is load-bearing for the brief's "pure function"
  claim** and is asserted explicitly in `test_cli_deterministic`
  (two CLI invocations produce byte-identical stdout). The
  per-question table is sorted by `question_id`; `k` values are
  sorted ascending. No timestamps, no random IDs, no dict-iteration
  ordering reliance.

## Follow-ups

### Filed as tasks

None. The candidates below are either drive-bys (none landed),
backlog material that already exists, or drops.

### Considered and dropped

- **Add `scorer*` to `pyproject.toml` package discovery.** A
  one-line fix, but: (a) MVP scoring runs via `python -m scorer`
  from a source checkout, (b) `retention-bench` isn't shipped as a
  wheel yet, (c) touching `pyproject.toml` is outside the M6
  `Touches:` declaration (`scorer/`, `tests/`). Should land
  whenever a packaging task arises (likely alongside B4 Docker
  packaging). Filing a separate task feels heavier than the
  one-line change deserves.
- **Determiner stripping ("the", "a", "an") in `_normalise`.**
  Tempting but opens a slippery-slope toward lemmatisation. M5's
  format-hint convention is the right place for this concern;
  scorer stays mechanical. Re-raise if smoke runs hit false
  negatives from a/an/the prefixes specifically.
- **CSV / JSON output mode in addition to the printed table.** The
  brief is explicit: printed table is sufficient. Real downstream
  consumers (leaderboards) will want structured output; punt to
  whatever post-MVP task introduces those consumers.
- **Variance / error-bar reporting** per `metrics.md`. Real but
  blocked on multi-seed runs, which is itself post-MVP. Drop until
  someone runs multi-seed.
- **Excluded-question count in the aggregate summary line.**
  Considered adding "(n_excluded=K)" alongside `n_usable`.
  Information is already visible in the per-question rows
  (`(excluded — C≈P)`). Don't gild the lily.

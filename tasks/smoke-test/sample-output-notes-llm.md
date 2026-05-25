# Smoke-test sample output — notes-LLM

Captured 2026-05-25 from a fresh run of the **notes-llm** reference SUT
against the Tell-Tale Heart smoke task (`claude-sonnet-4-6` via
Anthropic API, to match the no-state baseline run). Run ID:
`smoke-test-2026-05-25T12-51-56Z-34ca7c`.

Companion to `sample-output.md` (the no-state floor run); together these
show the first head-to-head reference-SUT comparison on the same task.
**This is the first non-flat retention curve produced by the harness.**

## Scorer output (terminal)

```
question_id | P | C | R(1) | norm_R(1)
q1 | 0.00 | 1.00 | 1.00 | 1.00
q2 | 0.00 | 1.00 | 1.00 | 1.00
q3 | 0.00 | 0.00 | 0.00 | (excluded — C≈P)
q4 | 0.00 | 0.00 | 0.00 | (excluded — C≈P)
q5 | 0.00 | 1.00 | 1.00 | 1.00

aggregate (k=1, n_usable=3): 1.00
```

## Head-to-head vs no-state

| Metric | no-state (`sample-output.md`) | notes-llm (this run) |
|---|---|---|
| Ceiling answers semantically correct | 5/5 (Sonnet knows the story) | 5/5 |
| Ceiling answers scored by exact-match | mixed; all 5 excluded via `C≈P` | 3/5 |
| `R(1)` on usable questions | n/a (none usable) | **1.00** |
| Aggregate retention | (empty by design — `READ` is no-op) | **1.00 over n=3** |

The exclusion behaviour differs because *no-state*'s ceiling equals its
prior (no learning possible), while *notes-llm*'s ceiling is 1.0 for
three questions and 0.0 for two — and `C≈P` excludes the two zeros.
Both exclusions are correct under the current exact-match scorer; the
notes-llm-side exclusions are scorer-brittleness false-negatives that
backlog **B3 (LLM-judge)** is intended to fix.

## Per-question answers

| qid | type | gold | sut ceiling (`evt-0003`) | sut retention (`evt-0005`) |
|---|---|---|---|---|
| q1 | surface_factual | `pale blue` | `Pale blue` | `Pale blue` |
| q2 | surface_factual | `seven` | `Seven` | `Seven` |
| q3 | entity_tracking | `the police` | `Three police officers` | `Three police officers` |
| q4 | surface_factual | `a heartbeat` | `The old man's heartbeat` | `The heartbeat (of the old man)` |
| q5 | multi_hop | `eighth` | `Eighth` | `Eighth` |

q3 and q4 are substance-correct in both probes but lose exact-match.
Retention answers come from `DIR/notes.md` only — the SUT no longer
has access to the source text at quiz time, so the consistency between
ceiling and retention demonstrates that **notes survived the `RESET`
on disk** and were sufficient to reconstruct correct answers.

Specific `sut_answer` strings are not reproducible across LLM runs;
the **shape** (5 events, full retention on usable questions, two
verbose-answer exclusions) is reproducible up to model nondeterminism.

## The notes file the SUT wrote

`DIR/notes.md` after the two `READ` events (Sonnet's choice of format
and content; the SUT's system prompt asks for cumulative notes
inside `<NOTES>…</NOTES>` tags and atomic-writes the parsed result):

```markdown
# The Tell-Tale Heart — Edgar Allan Poe (1843)

## Publication
- First published in *The Pioneer*, January 1843.

## Narrator & Setup
- Unnamed narrator insists he is sane, not mad — claims his "disease"
  only sharpened his senses (especially hearing).
- Lives with/cares for an old man he claims to love; no motive of
  money or grudge.
- Motive: the old man's "Evil Eye" — pale blue, filmed over, like a
  vulture's eye — makes the narrator's blood run cold.

## The Plan & Execution (7 Nights + 1)
- For 7 nights, narrator opens the old man's door at midnight, inserts
  a dark lantern, watches — but the eye is always closed.
- 8th night: thumb slips on lantern fastening → old man cries "Who's
  there?" and sits up.
- ... (and so on — full file in run dir, ~39 lines)
```

The notes are well-structured Markdown the model chose freely (the
system prompt does not prescribe format — it suggests bullets, prose,
or Q&A and asks the model to decide). The full file lives at
`runs/smoke-test-2026-05-25T12-51-56Z-34ca7c/dir/notes.md` and is
worth reading in full as a small qualitative artifact.

## Resource appendix (from `sut-manifest.json`)

```json
{
  "resource_appendix": {
    "kind": "api",
    "model_id": "claude-sonnet-4-6",
    "tokens_in": 5578,
    "tokens_out": 994,
    "api_call_count": 4,
    "wall_clock_ms": 27173
  }
}
```

4 API calls (2 `READ` + 2 `QUIZ`; one `QUIZ` per session, with the
post-`RESET` `QUIZ` happening in a fresh subprocess that reloads notes
from disk). The READ-event token counts are recorded thanks to the B1
harness widening of `_accumulate_resources()` to fire on every event
reply, not just `QUIZ`. At Sonnet 4.6 list prices, ~$0.032 USD.

## Run-manifest summary

```json
{
  "task_id": "smoke-test",
  "event_count": 5,
  "reset_count": 1,
  "sut_invocation_count": 2,
  "exit_status": "ok"
}
```

Same shape as the no-state run — the smoke task is fixed, the SUT
varies. Whatever curve the SUT can produce against this task is what
shows up.

## What this tells us

- **The cumulative-notes path works end-to-end on real material.**
  Two READs, with prior notes shown on the second, produced a coherent
  single notes file covering both halves of the story.
- **Notes survive `RESET` on disk.** Post-`RESET` answers come from
  `notes.md` only and match the ceiling answers — the full pipeline
  for cross-`RESET` retention is wired correctly end-to-end.
- **The exact-match scorer is the next real bottleneck.** Two of five
  questions worth of retention signal is being dropped on verbosity.
  Backlog item B3 (LLM-judge) is the fix; this run is the first
  concrete cost-of-not-doing-it data point.
- **A non-flat retention curve is now an audit-able artifact** — the
  trace, the per-question records, the notes file the SUT wrote, and
  the resource counts are all on disk in `runs/`. Outward-facing
  material on the benchmark can cite real runs, not hypotheticals.

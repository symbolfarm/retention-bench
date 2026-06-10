# C14 Public README rewrite + `.env.example`

**Priority:** high
**Blocked by:** C13
**Touches:** `README.md`, `.env.example`

## Context

The current `README.md` is the **pre-pivot** "Continual-Learning Eval (CL-N)"
scoping doc. It is wrong on multiple counts for a public reader (see
[[project_clbench_pivot]] and the B9 OpenAI-compatible port):

- Never mentions the CL-Bench pivot (2026-06-07); still frames the project as a
  standalone benchmark with five hardware tiers, two leaderboards, etc.
- **Quickstart is broken**: tells users to set `ANTHROPIC_API_KEY` and a
  `claude-haiku` default, but B9 (2026-06-03) moved all text SUTs + judge to an
  **OpenAI-compatible base URL / OpenRouter** (`deepseek/deepseek-v4-flash`
  default; judge `moonshotai/kimi-k2.6`).
- References internal artifacts that don't belong in a public face:
  `history/design-dialogue.md` (deprecated), the "Communication norms" and
  "What this project owes other projects" sections (internal joint-scoping +
  cross-project strategy).

This README is a **divergent variant** maintained directly on `main` (per C13) —
not snapshotted from `dev`.

## Goal

A lean, accurate, public-facing `README.md`: what the benchmark is *post-pivot*
(a reset + constructive extension on top of Continual Learning Bench), a working
quickstart against the OpenAI-compatible path, and pointers only to public docs.
Plus a `.env.example` the `.gitignore` already whitelists.

## Acceptance criteria

- [ ] Framing reflects the pivot: retention-bench extends CL-Bench (Asawa et al.)
      with a hard RESET (process-kill discontinuity, survive-dir persistence) and
      a constructive/parametric system class. Cite CL-Bench; link C15's NOTICE.
- [ ] Quickstart matches reality: OpenAI-compatible `base_url` + key env vars
      (`RETENTION_BENCH_BASE_URL`, the OpenRouter key, default model ids). Verify
      the exact env-var names against `retention_bench/` + `suts/` before writing
      — do not transcribe from memory.
- [ ] No internal sections: drop "Communication norms" and "What this project
      owes other projects"; remove links to `history/`, `feedback/`,
      `design-dialogue`, and any pre-pivot status block.
- [ ] Entry-points / docs list points only to public docs (the curated set from
      C16) — no `AGENTS.md` / `TASKS.md` / `.tasks/` links.
- [ ] `.env.example` created with the real env-var names (values placeholdered),
      matching the quickstart.
- [ ] Quickstart commands are accurate against `run.sh` (confirm the actual
      invocation; the old `./run.sh smoke` may have changed under the pivot).

## Relevant files

- `README.md` (rewrite), `.env.example` (new).
- Verify against: `run.sh`, `retention_bench/system.py`, `suts/*/` (env-var
  names, default models, base-url seam), `docs/clbench-pivot-plan.md`.

## Decisions already made

- README is a `main`-only variant (C13), not promoted from `dev`.
- Public face leads with the contribution (reset + constructive), CL-Bench as the
  base it extends — consistent with the C5 outreach framing (don't claim priority).

## Out of scope

- LICENSE/NOTICE files (C15) — README links to them but doesn't create them.
- Docs triage (C16) — README references the curated set but doesn't curate it.
- The C5 author-outreach draft (Toby's separate task).

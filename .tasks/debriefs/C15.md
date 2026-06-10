# Debrief: C15 LICENSE + CL-Bench attribution (NOTICE)

**Completed:** 2026-06-10
**Commit:** 541c48b

## What shipped

- **`LICENSE`** — verbatim Apache-2.0, with `Copyright 2026 Toby Lightheart /
  Symbol Farm` in the appendix notice.
- **`NOTICE`** — attributes Continual Learning Bench (Asawa et al.,
  arXiv:2606.05661, Apache-2.0); states it's consumed as a pinned-commit
  dependency (`cl-benchmark`), not redistributed here; records retention-bench's
  original contributions (hard RESET + constructive system class). Written to
  satisfy Apache-2.0 §4(d).
- **`pyproject.toml`** — `license` MIT → `{ text = "Apache-2.0" }`; added the
  Apache classifier + py3.13 classifier; `authors` now lists both Toby Lightheart
  and Symbol Farm.

## Descoped / deferred

- README link to LICENSE/NOTICE is left to **C14** (the brief allowed either task
  to land it; C14 owns the README rewrite).

## Design decisions

- **License = Apache-2.0; holder = "Toby Lightheart / Symbol Farm"** — both
  confirmed with Toby before writing.
- **No file-level license headers added.** Verified CL-Bench is a *pinned git
  dependency* (`cl-benchmark @ git+…@9cc63c0`), not vendored — our source only
  imports/adapts it (`retention_bench/_clbench.py` re-exports its interface; SUTs
  speak its wire contract). Since no upstream source is copied into the repo, a
  top-level NOTICE is sufficient and no per-file Apache headers are required.
- **No author email in `pyproject.toml`.** `pyproject` ships on the public `main`;
  left Toby's email out to avoid publishing it without being asked. The LICENSE/
  NOTICE identify the holder by name only.
- Used the `license = { text = "..." }` table form (not the PEP 639 SPDX string)
  to match the file's existing style and avoid a newer-setuptools requirement.

## Observations

- CL-Bench packages itself under a top-level `src` import path (a known packaging
  smell, already flagged in C0/C2 and routed to a possible C7 upstream PR) — not a
  licensing concern, but it's why the dependency is imported via the
  `retention_bench/_clbench.py` chokepoint rather than `src.*` directly.

## Follow-ups

### Considered and dropped

- *Per-file SPDX headers across our own source* — nice-to-have, but not required
  by Apache-2.0 and out of proportion for a 0.1 research artifact; the top-level
  LICENSE + NOTICE cover obligations. Not filing.

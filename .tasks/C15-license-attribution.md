# C15 LICENSE + CL-Bench attribution (NOTICE)

**Priority:** high
**Blocked by:** C13
**Touches:** `LICENSE`, `NOTICE`, `pyproject.toml`, `README.md` (license badge/section)

## Context

The repo has **no LICENSE file** — a hard blocker for publishing a credible public
artifact. retention-bench also **extends Continual Learning Bench** (Asawa et al.,
arXiv 2606.05661, **Apache-2.0**) and **reuses CL-Bench's harness/runner** via the
adapter seam (see [[project_clbench_pivot]]), so the derivation needs explicit
attribution, not just a license of our own.

LICENSE/NOTICE are `main`-only public files (maintained directly on `main` per
C13's divergent-file handling), though they can equally live on `dev` too.

## Goal

A clear license for retention-bench plus a NOTICE that attributes the CL-Bench
derivation in line with Apache-2.0's requirements, and `pyproject.toml` license
metadata that matches.

## Decisions to confirm with Toby before writing

- **License choice.** Apache-2.0 is the natural fit (matches CL-Bench, patent
  grant, NOTICE mechanism). Confirm vs MIT or other before committing — this is
  Toby's call. Default recommendation: **Apache-2.0**.
- **Copyright holder string** (e.g. "Symbol Farm" / Toby Lightheart) for the
  license header and NOTICE.

## Acceptance criteria

- [ ] `LICENSE` present (full text of the chosen license; Apache-2.0 unless Toby
      redirects).
- [ ] `NOTICE` attributes Continual Learning Bench (Asawa et al., Apache-2.0),
      states what is derived/reused (the harness/runner adapter path) vs original
      to retention-bench (hard RESET, constructive system class), and preserves
      any upstream copyright/notice as Apache-2.0 §4 requires.
- [ ] `pyproject.toml` `license` field (and classifier) matches the chosen
      license; `authors`/holder consistent with the NOTICE.
- [ ] README links to LICENSE + NOTICE (coordinate with C14; either can land the
      link).
- [ ] Check `suts/`, `harness/`, `retention_bench/` for any copied-or-adapted
      CL-Bench source that needs file-level attribution headers, not just a
      top-level NOTICE.

## Relevant files

- New: `LICENSE`, `NOTICE`.
- `pyproject.toml` (license metadata).
- Audit for derived code: `harness/sut_process.py`, `retention_bench/_clbench.py`,
  `retention_bench/system.py`.

## Decisions already made

- Attribution is required (Apache-2.0 upstream); a bare license is insufficient —
  a NOTICE describing the derivation is part of done.

## Out of scope

- Relicensing or contacting upstream (that's C5/C7 territory).
- README body rewrite (C14) — this task only ensures the license link exists.

# Debrief: RB-20 AGENTS.md refresh — DOWNGRADED TO CHORE

**Closed:** 2026-07-29 (same day it was filed)
**Status:** `superseded` — not task-sized; delivered directly.

Toby's call, generalising the RB-18 precedent: docs work done in one sitting by whoever is
already holding the context is a `docs:` commit, not a brief-and-debrief cycle.

Delivered in the same commit: the AGENTS.md rewrite plus `tests/test_docs_links.py`.

**One finding worth keeping.** The obvious fix — a markdown link checker — would NOT have
caught this failure. The stale AGENTS.md contained **zero** markdown links; all 25 of its
dead references were backticked paths (`docs/decisions-checklist.md` and friends). The test
therefore has two checks, and the backtick check is the one that matters for orientation
docs. Verified against the pre-rewrite file: 25 dead refs detected.

`TASKS.md` is deliberately excluded from the backtick check — its Historical sections name
deleted files in order to say they were deleted, and it cites constructive-retention
debriefs that legitimately do not exist in this repo. Both would fire as false positives,
and a noisy test gets muted.

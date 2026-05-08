---
title: Design dialogue — continual-learning-eval scoping
project: continual-learning-eval
status: in-progress (joint-scoping pilot #2 of the design-dialogue artifact)
started: 2026-05-08
participants: Toby, Claude
---

# Design dialogue — continual-learning-eval

Joint-scoping record for the continual-learning-eval project. Picks up
from the conversation in which CNN scoping read the v0.1 spec and
identified that the constructive-net case lives in `extensions.md`
rather than v1 — which made the eval's own scoping a precondition for
CNN branch-promotion.

Format: dated turn-by-turn. "Agreed:" markers capture decisions that
should not be re-litigated without explicit reopening. Open questions
sit at the bottom of each turn until answered.

---

## Turn 1 — 2026-05-08 (Claude)

### Echo-back: what the v0.1 spec actually scopes

CL-N v0.1 (now [[spec]] + 7 reference docs) defines a benchmark with:

- **Discontinuity primitive**: process restart.
- **Memory primitive**: persistent filesystem at a designated path.
- **SUT contract**: LLM-agent black box; the six-thing interface in [[interface]].
- **Headline metric**: retention curve — task score as a function of N restarts.
- **Reference SUT modes**: pure LLM, notes-LLM, full-harness.

Everything that doesn't fit the agent+filesystem+restart shape — weight
updates, multi-agent, adversarial perturbations, cross-task transfer,
failure-mode diagnostics — got pushed into [[extensions]] as deferred.

The **weight-update extension** (deferred) is the case constructive-
neural-networks research actually needs: discontinuity = a weight
update or a structural growth event; persistent state = the weights
themselves. The extensions doc explicitly notes this is "particularly
interesting for constructive-network research."

### The reframing

The v1-vs-extension distinction is a **scoping decision**, not a
structural truth. The retention curve, the staged DAG, and the
"discontinuity = anything that could lose information" framing all
generalise across both flavors. What changes is the SUT contract.

Toby's actual position (2026-05-08):

- **Constructive case is the priority** (his research interest).
- **Agent-memory case stays in scope** — it's where any external
  interest will land first, since most current memory-system work is
  in that regime.
- Therefore **not** two co-equal tracks; rather: **two tracks with
  constructive prioritized in scoping decisions, agent-memory kept as
  the externally-legible track.** When design tensions arise, the
  constructive case wins, but agent-memory keeps its seat at the
  table.

**Agreed (2026-05-08):**
1. The eval is one protocol with two tracks, not one protocol with a
   headline track + extension family.
2. Constructive (weight-update / structural-growth) track is the
   priority track for scoping decisions.
3. Agent-memory track remains in scope and keeps the externally-
   legible framing.
4. The v0.1 docs are *reference material* under joint-scoping
   treatment, not stable specifications.

### Open questions for Turn 2

The agreed two-track framing immediately raises a stack of scoping
questions. Three candidates for what to chase first, ranked:

1. **Interface-contract delta first.** What changes in the SUT
   contract going from agent-memory to constructive-track? The
   six-thing contract in [[interface]] (task prompt, action budget,
   filesystem path, clear schedule, awareness flag, stage outputs)
   was written for agents — what's the analogue for "the SUT is a
   model + a construction procedure"? Concretely: what's a "stage
   prompt" when there's no LLM to read it? Is there a per-stage
   "training data" instead? What replaces the filesystem-as-memory?
   (Probably: weights themselves + optional replay buffer + optional
   constructive-state.) **Claude's pick** — it's the smallest
   surface that, once roughed in, makes everything downstream
   answerable.

2. **Worked-example task first.** Pick one task track from
   [[tasks]] (book-episodic or codebase) and walk through what it
   would look like in the constructive flavor. Forces concreteness;
   may surface that the existing task structure doesn't transfer at
   all, which would be load-bearing. Risk: the worked-example
   anchors the scoping in one task's idiosyncracies before the
   protocol-level questions are answered.

3. **Open-questions triage first.** [[open-questions]] has 13 items
   stratified by blocking-status. Re-rank them under the two-track
   framing — which become "agent-track only," which become "both
   tracks," which become "constructive-track only," and which
   dissolve. Cheap re-organisation that produces a sharper worklist.
   Risk: may be premature without the interface-contract delta.

### Open questions not part of the ranking

- **Project slug for the constructive track itself.** Is it a track
  *name*, e.g. "weight-update CL," or does it want a sharper name
  that doesn't lead with the agent-memory framing's vocabulary?
  ("Catastrophic-forgetting CL" reads dated; "structural-growth CL"
  is too narrow if the track also covers fine-tuning.) Defer to a
  later turn.
- **Whether the spec's CL-N name survives.** "CL-N" was branded
  around the agent-memory track. May need a name that more honestly
  covers both tracks. Defer.
- **What the constructive-track's reference SUT looks like.** The
  agent-memory track has three reference SUTs (pure LLM, notes-LLM,
  full-harness). The constructive track presumably wants its own
  reference set — at minimum a baseline that does NOT preserve
  state (e.g. fine-tune-then-reset) so the retention curve has a
  meaningful zero. Defer until Turn 2 or 3.

---

*Turn 2 awaiting Toby's response on the ranked options above.*

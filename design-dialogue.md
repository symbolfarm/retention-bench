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

## Turn 2 — 2026-05-09 (Claude)

### Echo-back

Toby picked option 1 (interface-contract delta) and added a design
constraint: **ideally one interface covers both tracks, if achievable
without over-complicating.** This turn answers that question.

### Direct answer

Yes — achievable, and it doesn't over-complicate. The six-thing
contract generalises cleanly *if* we accept one reframing of what
"discontinuity" means in the constructive track. That reframing is
flagged below and is the only thing that needs explicit confirmation
before locking the unified interface.

### The unifying move

Rename two slots; everything else stays as-is:

| v0.1 slot (agent-memory) | Unified slot | Constructive instantiation |
|---|---|---|
| Task prompt | **Stage input** | Training data + objective (or eval input) |
| Action budget | Action budget | Training-step / FLOP / wall-time cap |
| Persistent filesystem path | **Persistent-state directory** | Checkpoint dir (weights + optional replay buffer + optional structural state) |
| Clear schedule | Clear schedule | Same |
| Awareness flag | Awareness flag | Same |
| Stage outputs | Stage outputs | Per-stage predictions on held-out set |
| Filesystem side effects | Persistent-state side effects | Checkpoint writes |

Observation set (tokens, time, tool calls, fs size/delta) is
parameterised per task — agent-memory tasks observe tokens; constructive
tasks observe training-steps / params-changed. Same *contract*
("harness records resource usage without SUT cooperation"), different
units.

The harness's actual job is unchanged: deliver stage input → run SUT
under budget → kill process → only the designated directory survives →
relaunch → repeat. A constructive SUT is one that, on relaunch,
deserialises weights from the directory and continues training; an
agent SUT is one that reads notes from the directory and continues
reasoning. The harness doesn't need to know which.

### The reframing that needs confirmation

**PENDING CONFIRMATION:** In the unified interface, the eval-relevant
**discontinuity is the stage boundary / process restart**, in both
tracks. Weight updates are internal-to-session activity, not
discontinuities themselves.

This contradicts the framing in v0.1 [[extensions]]
("discontinuity = a weight update or a structural growth event").
Reasons to adopt the stage-boundary framing instead:

1. It's the **standard CL literature framing** — task boundaries are
   the discontinuities; intra-task gradient steps aren't.
2. It's what makes the **retention curve metric** meaningful: x-axis =
   stages, not gradient steps. (A weight-update-as-discontinuity
   x-axis would have ~10⁵ ticks per "task" and the curve becomes
   noise.)
3. It's the only framing under which **one interface** covers both
   tracks without bolting on a second harness.

Cost of adopting it: weight-update-CL papers that frame each update
as a discontinuity-of-interest don't map directly. But I think those
are rare; most CL work is task-boundary-framed.

### Where unification is forced (honest accounting)

Two places where the unified interface is slightly stretched:

1. **"Tool calls" as an observation.** Meaningful for agents,
   meaningless for a constructive SUT that just runs SGD. The fix:
   declare the observation set as task-parameterised (already implied
   by v0.1, just needs to be made explicit). Not an interface change,
   just a clarification.

2. **"Notes mode" reference SUT doesn't have a constructive analogue.**
   The three v0.1 reference modes (pure LLM / notes / full harness)
   are all agent-flavored. The constructive track will need its own
   reference-mode set (probably: no-state baseline / naive
   fine-tune-and-checkpoint / replay-buffer / EWC-or-similar /
   constructive-growth). This is *not* an interface concern —
   reference modes are above the interface — but it's the next thing
   the constructive track needs and Turn 1 already deferred it.

### What's now in scope

If Toby confirms the discontinuity reframing, the unified interface
spec is essentially [[interface]] with the two renames above and an
explicit note that observation units are task-parameterised. The
rewrite is small.

### Pending Toby

1. **Confirm or push back on the discontinuity reframing** (stage
   boundary, not gradient step). This is the load-bearing decision.
2. **Confirm the two renames** (stage input, persistent-state
   directory) or propose alternatives.
3. **Direction for Turn 3.** Two natural follow-ups, ranked:
   - **3a. Worked-example sanity check.** Take one task from
     [[tasks]] and walk it through both tracks under the unified
     interface. Catches over-abstraction. **Claude's pick** — the
     unified interface is currently a paper exercise; one concrete
     pass through it is the cheapest validation.
   - **3b. Constructive-track reference modes.** Design the
     constructive analogue of pure-LLM/notes/full-harness. Higher
     value long-term but assumes the unified interface holds; better
     to pressure-test 3a first.

---

## Turn 3 — 2026-05-09 (Claude + Toby)

### Echo-back

Toby pushed back on Turn 2's framing: many constructive-NN algorithms
aim to **avoid SGD entirely**, so collapsing "weight update" and
"structural growth event" into one kind of discontinuity was the wrong
move. Toby's preference: **agnostic discontinuity** — the harness
shouldn't know or care which mechanism (SGD, structural growth, agent
notes) is happening behind the veil. Same interface for all SUT types,
mechanism is the SUT's private business.

Claude sketched a concrete worked example (harness loop + SUT-type
table covering notes-LLM, constructive net, SGD fine-tune, vector
store, EWC). Toby endorsed: *"captures my idea very well... incorporate
this going forward."*

### Backstory on the v0.1 conflation (for the record)

The v0.1 [[extensions]] section *Weight-update / catastrophic-forgetting CL*
lumped EWC, LoRA, replay, and **constructive growth** into one bullet,
on the reasoning that all four put "the persistent state inside the
model parameters/structure." Turn 1's "weight update or structural
growth event" phrasing was Claude compressing that bullet. The
compression hid that constructive growth and SGD-driven CL are
*different mechanisms* (discrete add-a-unit events vs. continuous
gradient flow), even though they share the property of internal-to-
model state. The agnostic-interface resolution dissolves the
conflation by not relying on the distinction at all.

### Agreed (2026-05-09)

5. **Discontinuity is fully mechanism-agnostic.** The primitive is
   `process.kill()` + "only the persistent-state directory survives."
   The harness has no awareness of what the SUT does internally — SGD
   steps, growth events, LLM calls, vector-DB writes are all
   indistinguishable from the harness's perspective.

6. **The contract is five things, not six.** STAGE_INPUT in,
   STAGE_OUTPUT out, persistent-state directory, action budget,
   optional clear schedule + awareness flag. (The v0.1 six-thing
   framing folded "task prompt" and "stage outputs" as separate
   first-class items; the unified framing treats them as the contents
   of the input/output files.)

7. **Reference SUT modes proliferate but live above the interface.**
   The notes-LLM / constructive-net / SGD-fine-tune / vector-store /
   EWC examples in the worked sketch are all *reference modes*, not
   separate protocol tracks. Any process that conforms to the file
   protocol is a valid SUT.

8. **Resource observation is task-parameterised.** Tokens for agent
   tasks, gradient-steps for SGD tasks, growth-events for constructive
   tasks. Wall-clock and persistent-directory size/delta are observed
   universally.

### The worked sketch (canonical reference)

Harness loop (identical for every SUT type):

```
DIR = persistent-state directory (empty at stage 1)

for stage in 1..N:
    proc = spawn_sut(persistent_dir=DIR)
    write(DIR/"STAGE_INPUT",  stage_input(stage))
    write(DIR/"STAGE_META",   {stage, total, awareness})
    proc.signal_start()
    proc.wait(budget=B)
    output = read(DIR/"STAGE_OUTPUT")
    scores[stage] = score(output, ground_truth(stage))
    snapshot(DIR)
    proc.kill()                  # discontinuity!
    # only DIR survives; next iteration spawns fresh.
```

Per-SUT instantiation differs only in directory contents + internal
mechanism:

| SUT type | Reads from DIR | Internal mechanism | Writes to DIR |
|---|---|---|---|
| Notes-LLM agent | `notes.md` | LLM call(s) + reasoning | updated `notes.md`, `STAGE_OUTPUT` |
| Constructive net | `network.pkl` (structure + weights) | growth events, possibly no SGD | updated `network.pkl`, `STAGE_OUTPUT` |
| SGD fine-tune | `checkpoint.pt` | N epochs of gradient updates | updated `checkpoint.pt`, `STAGE_OUTPUT` |
| Vector-store agent | `chunks.db`, retrieval index | retrieve + LLM call | updated `chunks.db`, `STAGE_OUTPUT` |
| EWC fine-tune | `checkpoint.pt`, `fisher.pt` | gradient updates w/ EWC penalty | updated checkpoint + fisher, `STAGE_OUTPUT` |

### Implications for prior agreements

- **Turn 1 agreement #1** (one protocol with two tracks) **softens**:
  there is one protocol with one mechanism-agnostic interface; the
  "two tracks" are now better described as **two areas of focus** for
  *task design* and *reference-mode design*, not as bifurcations of
  the protocol.
- **Turn 1 agreement #2** (constructive prioritized) **stands** but
  applies to which tasks and which reference modes get designed first,
  not to interface design.
- **Turn 1 agreement #3** (agent-memory stays in scope) **stands**.
- **Turn 1 agreement #4** (v0.1 docs are reference) **stands and
  intensifies** — [[interface]] in particular needs a rewrite to match
  the five-thing agnostic contract; [[extensions]]'s "Weight-update /
  catastrophic-forgetting CL" section needs revisiting (probably
  dissolves — those algorithms become reference modes).

### Pending Toby — direction for Turn 4

Three candidates, ranked:

1. **Pressure-test the unified interface with one real task.** Pick a
   task from [[tasks]] (book-episodic or codebase) and walk it through
   *at minimum* a notes-LLM SUT and a constructive SUT under the
   five-thing contract, end-to-end. Catches over-abstraction; produces
   a concrete artifact that downstream rewrites can lean on.
   **Claude's pick** — the sketch in this turn is illustrative, not
   validated; one real walkthrough is the cheapest way to find what's
   broken.

2. **Rewrite [[interface]] to match the five-thing agnostic contract.**
   The sketch above is sufficient material to do this directly.
   Mechanically simpler than option 1; risks locking in errors that
   option 1 would have caught.

3. **Reference-mode design for the constructive area.** Sketch the
   minimum set of reference SUTs the constructive area needs (no-state
   baseline, naive checkpoint-and-grow, replay-buffer-augmented, etc.)
   so the constructive-NN project has anchors to compare against.
   Higher long-term value but assumes the interface holds.

---

*Turn 4 awaiting Toby's response on direction.*

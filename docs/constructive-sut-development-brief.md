# Constructive Neural Network SUT — Development & Integration Brief

> **Audience.** An AI agent (Claude) building a *constructive neural network*
> (CNN — a model that grows its own capacity and mutates its weights as it
> learns) in its **own project/repository**, which must plug into **Retention
> Bench** as an external system-under-test (SUT). This document is the contract
> the model must honour to be measured here, plus practical/theoretical guidance
> on building the model itself. Read Part A as **requirements**; Parts B–C as
> **suggestions** — adopt, adapt, or argue with them.
>
> **Status:** drafted 2026-06-08 against retention-bench at commit `5f0b376`
> container-launch support landed. The integration seam is stable; the development guidance is a
> starting position, not a settled design.

---

## 0. Why this split exists

Retention Bench is a **measurement harness**, not a model. It is an extension on
top of the Continual Learning Bench (Asawa et al.) that adds two things CL-Bench
lacks: a **hard RESET** (a process-kill discontinuity where only an on-disk
"survive-dir" persists) and a **constructive/parametric system class**. Your
model is the *first serious instance* of that system class.

Keeping the model in its own repo is deliberate:

- **Separation of concerns.** The benchmark measures; the model is measured. A
  benchmark that ships its own evolving headline SUT is harder to trust and
  harder to keep stable. The numbers should not churn every time you tweak an
  optimizer.
- **The seam is built for it.** Retention Bench already drives SUTs as
  **external processes** (or external **containers**) over a simple
  JSON protocol. A model in another repo, shipped as a container image that
  speaks the protocol, plugs in with zero benchmark changes.
- **Iteration independence.** You want a tight train→eval→tweak loop; the
  benchmark wants stability. The container boundary keeps both honest.

The research frame this serves: **episodic → understanding transfer** — whether a
system can convert specific experiences into reusable understanding that
generalizes to new instances. That capacity is argued to be a missing ingredient
for general / weakly self-improving AI. The constructive angle is that *growing
capacity* (rather than only overwriting fixed weights) is a candidate mechanism
for accumulating understanding without catastrophic forgetting. Retention Bench's
gain-vs-`k` curve is how we put a number on it.

---

## Part A — Integration contract (REQUIREMENTS)

To be a valid retention-bench SUT, the model is wrapped in a thin adapter process
that speaks the wire protocol below. The reference implementation is
[`suts/constructive/`](../suts/constructive/) — a tiny from-scratch byte-level
transformer that grows one block and trains a few steps per instance. It emits
**gibberish on purpose** (it is an integration example, not a quality baseline);
your job is to keep the contract and make the *content* good.

### A.1 Process & I/O model

- The SUT is a **long-lived process**. It is spawned once, then handed many
  requests over its lifetime, one JSON object per line on **stdin**, replying one
  JSON object per line on **stdout**. `stderr` is free for logs.
- **Flush every reply** (line-buffered / explicit flush). The harness blocks on a
  single reply line per request with a wall-clock timeout (default 300s/request).
- The working directory is the **survive-dir** (`DIR`); `RETENTION_BENCH_DIR` also
  points at it. In container mode `DIR` is bind-mounted at `/dir`.

### A.2 Wire schema (the CL-Bench path — what you implement)

**Request** (harness → SUT, one line):

```json
{"prompt": "string",
 "instance_id": "string-or-null",
 "instance_index": 0,
 "response_schema": { /* JSON Schema the action MUST conform to */ },
 "feedback": "string-or-null"}
```

**Reply** (SUT → harness, one line):

```json
{"action": { /* fields matching response_schema */ },
 "resource": {"flops": 0, "tokens_in": 0, "tokens_out": 0, "model_id": "…"}}
```

- **`action` MUST validate against `response_schema`.** The runner does
  `response_schema(**action)` and a mismatch crashes the run. The task supplies
  the schema per query (e.g. blind_spectrum_monitoring wants a `ScanReport`).
  Generate model-derived values, then coerce/synthesize into the schema — never
  emit free text where a structured object is required. (The reference SUT
  includes a generic JSON-Schema→value walker you can crib.)
- **`resource` is optional but expected.** Recognised keys (`flops`,
  `tokens_in`, `tokens_out`, `model_id`) are lifted onto a `compute` usage event;
  the whole dict is preserved. For a parametric model **report `flops` honestly**
  (a forward+backward step is the unit of cost the benchmark cares about) plus
  whatever else characterises the run (`param_count`, `growth_count`, `n_layers`).
  Self-reported numbers may later be cross-checked at the wire (token proxy), so
  do not inflate them.
- `feedback` is non-null only on **multi-step** tasks (see A.6).

### A.3 The hard RESET — the load-bearing requirement

A RESET is **`SIGKILL` + respawn**. There is **no shutdown hook, no flush
opportunity, no in-memory carry-over.** The *only* thing that survives is what you
have already written to `DIR`. Therefore:

1. **Checkpoint to `DIR` _before_ you write the reply line** for any instance
   whose state must survive. (The reference SUT flushes the checkpoint, then acks.)
2. **On spawn, reload from `DIR` if a checkpoint exists** (resume); otherwise
   cold-init. A fresh post-RESET process must reconstruct the exact model and
   continue as if uninterrupted.
3. Write checkpoints **atomically** (temp file + `os.replace`) so a kill mid-write
   never leaves a corrupt checkpoint.

The harness owns *when* resets happen (the reset schedule / `k`-axis); you never
schedule them. You only have to survive them. The discriminator the benchmark
measures: a model that genuinely retains scores above a model whose survive-dir is
wiped each reset (the stateless baseline).

### A.4 Constructive requirements (the system-class definition)

What makes this SUT "constructive" rather than just "stateful":

- **Weights mutate and/or capacity grows across instances** — the model is not a
  frozen base with an external memory; the *parameters themselves* carry learning.
- **Growth must round-trip through the checkpoint.** Save the architecture
  **config first**, so a fresh process rebuilds the (possibly grown) shape
  *before* `load_state_dict`. A variable-size checkpoint that a post-RESET process
  can load is the whole trick. (The reference SUT: `{config, model_state, meta}`.)
- **Growth should be auditable** — report `growth_count` / current shape in
  `resource` so the storage/compute accounting reflects the construction event
  (capacity growth shows up as a storage-delta jump and a param-count change).

### A.5 Determinism & offline

For the public-credibility goal, a reviewer must be able to reproduce a curve:

- **Seedable** (`*_SEED` env var) → deterministic init and training given the seed.
- **Offline at runtime** — no network calls, no model downloads during a run.
  Bake any base weights into the image. (If you bootstrap from a pretrained base,
  vendor it; don't fetch at runtime.)

### A.6 Single-shot vs. multi-step (know which you're targeting)

CL-Bench tasks come in two shapes:

- **Single-shot** (e.g. `blind_spectrum_monitoring`, the current target): one
  `respond()` per instance → terminal outcome. **Start here.**
- **Multi-step / agentic** (poker, SQL, etc.): the runner calls `respond()`
  repeatedly *within one instance*, feeding the prior step's observation back via
  `feedback`, until done. Supporting these needs a turn-taking adapter (deferred) and a
  real design decision for a constructive model: **do you take a weight update on
  every intra-instance observation, or only at the instance boundary?** Decide and
  document; the answer changes what "retention" even means for your model.

### A.7 Container packaging

The image is launched as:

```
docker run -i --rm --name <unique> -v <DIR>:/dir -w /dir \
  -e RETENTION_BENCH_DIR=/dir [-e DECLARED_VAR …] <image> <entrypoint…>
```

Requirements:

- The SUT package is **installed in the image**; the entrypoint resolves there
  (no host PYTHONPATH injection in container mode).
- Env is forwarded **by name only** — declare every var you need in the manifest's
  `env` array; undeclared vars are invisible inside the container.
- **Run as a non-root user**, and **write only to `/dir`.** (Retention Bench's own
  images are planned to move to non-root; bind-mounted files written as root
  are a cleanup/permissions hazard on the host. Match that.)
- Keep it **CPU-runnable** for cheap iteration; a GPU path can be additive later.

---

## Part B — Building the model (SUGGESTIONS)

These are starting positions, not requirements. The goal is a model whose
*retained, grown state measurably improves task reward* — and, ideally, improves
it through **understanding** (reusable structure) rather than **stenography**
(verbatim caching of past instances).

### B.1 Growth mechanisms

Decide what "grows" and how a growth event preserves prior function:

- **Depth** — add transformer blocks. Cheapest to make function-preserving:
  initialise a new block as (near-)identity (zero-init the residual branches) so
  adding it doesn't perturb outputs, then let training specialise it.
- **Width** — grow `d_model` / heads / MLP hidden. Function-preserving width
  growth (Net2Net-style) copies/zero-pads so the larger model computes the same
  function at the moment of growth, avoiding a loss spike.
- **Embeddings / vocab** — relevant if the input alphabet expands.

**Function-preserving vs. fresh-init growth** is the key trade: function-preserving
avoids destabilising what's already learned (good for retention) but constrains the
new capacity's starting point; fresh-init is more flexible but risks a forgetting
spike right when you grow. For a *retention* benchmark, bias toward
function-preserving and measure the forgetting cost of each growth event.

### B.2 When to grow (triggers)

- **Scheduled** (every N instances) — simplest, what the reference SUT does (grow
  once). Good for a first curve.
- **Saturation-triggered** — grow when train loss plateaus or gradient-norm /
  capacity signals say the current size is saturated. More principled, more moving
  parts.
- **Drift-triggered** — grow at concept-drift boundaries. Retention Bench can place
  resets *on vs off* drift boundaries (`blind_spectrum_monitoring` drifts at
  instance 30/60/90); aligning growth with drift is a natural experiment — does
  adding capacity *at* a drift boundary preserve the old regime better than
  overwriting?

### B.3 Forgetting is the adversary — make growth earn its keep

The benchmark exists because fixed-capacity continual learning forgets. Constructive
growth is one mitigation (add capacity for the new rather than overwrite the old —
a form of *parameter isolation*). Worth comparing against / combining with the
classics so you know growth is pulling its weight:

- **Replay** (rehearse past instances from the survive-dir) — cheap, strong, and
  *legitimate here* because the survive-dir is your sanctioned memory. But note:
  pure replay of verbatim instances is the **stenography** failure mode the
  research frame wants to see *past*. Use replay as a baseline to beat on the
  understanding axis, not as the whole answer.
- **Regularisation** (EWC-style) — protect important weights. Composes with growth.
- **The constructive bet:** new knowledge lands in new parameters, so old
  parameters drift less. Measure whether your growth actually delivers this
  (forgetting on early instances after later growth).

### B.4 Curriculum & "developmental" training

A tiny-model-first, developmental curriculum is the intended fast-iteration core:
start tiny, grow as task complexity rises. Practically — get a *small* model
producing a non-degenerate curve on the single-shot target before scaling. The
first milestone is **shape**, not SOTA.

### B.5 Understanding vs. stenography — the real target

The differentiating signal is whether retained state encodes **reusable structure**
or **memorised instances**. `blind_spectrum_monitoring` is chosen precisely because
its latent channel structure is *stable but not verbatim-recoverable* — a notepad
of past observations only partly helps; inferring the latent structure helps more.
To make the distinction legible:

- Aim for a model that improves on **held-out / novel** instances drawn from the
  same latent structure, not just on repeats.
- Retention Bench can break the curve down by question type and (via later curriculum work,
  if built) decompose reward into a shallow-recall vs. deep-adaptation component.
  Design so those two components **diverge** for your model — that divergence is
  the episodic→understanding-transfer signal, the headline result.

### B.6 Practical

- **CPU-first.** The reference SUT runs the smoke task in seconds on CPU; keep
  yours cheap enough to sweep many `k` values. Add GPU as an opt-in, not a
  dependency.
- **Checkpoint discipline.** Atomic writes, config-first, every boundary. This is
  where RESET bugs hide.
- **Account honestly.** Real FLOPs per step; growth events visible in the storage
  delta. The accounting is part of the artifact's credibility.
- **Structured output.** The task dictates a `response_schema`; you need reliable
  schema-conforming output. For a from-scratch generative model, synthesise the
  structured object from model outputs (don't rely on free-form generation
  parsing); for a model with constrained decoding, use a grammar.

---

## Part C — How you'll know it's working (milestones)

Develop against Retention Bench's **gain-vs-`k` curve** as the north star
(`python -m retention_bench.gain_curve …`; see `docs/metrics.md`). Milestones, in
order:

1. **Plumbing.** Your SUT runs through `SubprocessSystem` on
   `blind_spectrum_monitoring` and returns a valid `TaskResult` (no contract
   crash); state survives a hard RESET (post-reset process loads the checkpoint).
   *The reference SUT already clears this bar — copy its shape.*
2. **Non-degenerate band.** The ceiling `C` (no-reset, full state) scores
   **measurably above** the stateless prior `P`, so the band `C − P` is no longer
   `EXCLUDED`. **This is the first real result** — it means retained, grown state
   helps the task. (Today every SUT reports `EXCLUDED`; clearing this is the gap.)
3. **A shaped retention curve.** `R(k)` degrades gracefully as reset density `k`
   rises, and ideally shows structure around drift boundaries (on-vs-off-drift
   reset placement). A monotone-ish decline with a knee is the artifact.
4. **Understanding > stenography.** The deep-adaptation reward component (or
   held-out/novel-instance performance) separates from the shallow-recall
   component — the model generalizes retained experience, not just caches it.

Milestone 2 is the one that unblocks everything downstream (a credible
public artifact, author outreach). Optimise for it first.

---

## Part D — Open decisions for the builder

These are yours to make; flag them back when you've chosen:

- **Growth axis & policy** (depth? width? function-preserving? trigger?).
- **Base: from-scratch vs. pretrained-and-grow.** From-scratch is cleaner for the
  "construction" story and reproducibility; a small pretrained base may reach
  milestone 2 faster but complicates the offline/vendoring requirement.
- **Intra-instance update policy** for multi-step tasks (per-step vs. boundary).
- **Memory beyond weights?** Are you purely parametric, or do you also use the
  survive-dir for replay buffers / notes? Both are allowed; be explicit, because
  it changes whether you're testing parametric understanding or hybrid memory.

---

## Pointers

| What | Where (in retention-bench) |
|---|---|
| Reference constructive SUT (worked example) | `suts/constructive/` (+ its `README.md`) |
| Wire protocol & launch modes | `docs/sut-interface.md`; `retention_bench/system.py` docstring |
| The SUT-as-CL-Bench-system adapter | `retention_bench/system.py` (`SubprocessSystem`) |
| Reset schedules / `k`-axis | `retention_bench/reset_schedule.py` |
| Gain-vs-`k` curve + metric definitions | `retention_bench/gain_curve.py`; `docs/metrics.md` |
| Design history (pivot rationale; task triage) | `docs/archive/` on the `dev` branch (not part of the public snapshot) |
| Upstream benchmark | Continual Learning Bench (Asawa et al.), Apache-2.0 |

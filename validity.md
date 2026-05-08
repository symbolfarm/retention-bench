# Validity and Contamination

CL-N tries to measure something specific: how well a system's *memory architecture* preserves task-relevant information across clears. Anything that lets a SUT score well *without* exercising its memory architecture is a confound.

This document enumerates the main confounds and the guardrails against them.

## Confound 1: Pretraining contamination

Books, papers, popular codebases, and well-known datasets are in pretraining corpora. A model that "remembers" a fact post-clear may simply be reciting it from weights.

### Mitigations

- **Asset selection:** prefer recent, niche, or private materials. Track and report contamination likelihood per asset.
- **Trajectory-specific questions:** ask about *what the SUT did or noted in earlier sessions*, not facts the model could know without ever reading the input. "What did you decide about character X in stage 2?" is robust; "What is character X's name?" is not.
- **Modification:** for public assets, modify them. Rename symbols in code; alter names, dates, places in text. The version the SUT processes is provably not the pretraining version.
- **Procedural / synthetic content:** for a portion of each track, use generated content. Loses ecological realism, gains contamination immunity. Ideally each track includes both real and synthetic assets so cross-validation is possible.

## Confound 2: Re-derivation

If the SUT can re-derive information instead of recalling it, the benchmark partly measures cleverness rather than memory.

### Mitigations

- **No re-reads as default.** The book track removes the original text after each stage. The codebase track defaults to graded no-re-reads (no re-reading of files already accessed pre-clear).
- **Trajectory-specific questions** (as above) are also a defence here: the SUT cannot re-derive its own past notes from the source material.
- **Reporting:** when a task is run with re-reads allowed, score that variant separately. The gap between no-re-reads and free-re-reads scores is itself an interesting measurement.

## Confound 3: Task-leak via the prompt

If session `k`'s prompt accidentally restates information from session `k-1`, the SUT does not need to remember it.

### Mitigations

- **Prompt audit.** Each task's per-session prompts are reviewed for inadvertent recapitulation.
- **Minimal stage prompts.** A stage prompt should specify *what to do*, not summarise what came before.
- **Pointer convention (where used).** If the harness tells the SUT "your stage 1 artifact is at path X," that pointer should be just a path, not a summary of the artifact's contents.

## Confound 4: Variance masquerading as signal

LLMs are stochastic. A small score difference between SUTs may be noise.

### Mitigations

- **Multiple seeds per `N`.** Default at least 3, more for high-variance tasks.
- **Report variance.** Curves with error bars; summary statistics with confidence intervals.
- **Cross-task correlation.** A SUT that wins on one track but loses on another is more likely to be picking up task-specific tricks than genuine memory capability.

## Confound 5: Overfitting to the benchmark

Once a benchmark is published, agent designers will optimise for it. Some optimisation is legitimate (better memory architecture); some is gaming (writing exactly enough notes to pass exactly these questions).

### Mitigations

- **Held-out tasks.** Maintain a public set for development and a held-out set for evaluation. Rotate periodically.
- **Procedural generation** (where a track supports it) makes the held-out set effectively infinite.
- **Diverse question types.** A SUT that handles surface facts but fails thematic synthesis is overfit; broad question coverage exposes this.
- **Cross-track reporting.** Scoring well only on one track is a signal; the leaderboard should make this visible.

## Confound 6: Mode confusion

Comparing a "pure LLM" SUT to a "full harness" SUT can produce results that reflect the underlying model's capability rather than the memory architecture.

### Mitigations

- **Mode-stratified reporting.** Pure LLM, notes mode, and full harness are reported as separate categories. Cross-category comparison is meaningful but should be done explicitly, not implicitly.
- **Same-model comparison.** Where possible, compare modes using the same underlying LLM. The lift from notes mode over pure LLM, holding the model fixed, is the cleanest measurement of "what does the scaffold add."

## Confound 7: Filesystem-as-side-channel

A clever SUT could use the filesystem to preserve information beyond what counts as "memory" in a meaningful sense — e.g., dumping the entire stage prompt verbatim into a file, then reading it back.

This is partly handled by the no-re-reads constraint on inputs (the original text is not on the filesystem; only what the SUT explicitly wrote is). But for ambiguous cases:

### Mitigations

- **Filesystem snapshots.** Snapshots are taken at every clear. Anomalously large or anomalously verbatim filesystems can be flagged in post-hoc analysis.
- **Filesystem-size metric.** A SUT that scores well only by writing massive verbatim dumps will show a pathological filesystem-growth curve. This is visible in the resource metrics, and readers can judge whether to trust the score.

## What we are *not* trying to control for

Some things are not confounds; they are part of what the benchmark legitimately measures.

- **Underlying model capability.** A more capable model will score higher. This is intended. The benchmark measures "this SUT, including its model and its memory architecture." Mode-stratified reporting prevents this from confounding architecture comparisons.
- **Inference cost.** A SUT that scores well at high token cost is a legitimate point on the cost/quality frontier. Resource metrics make this visible; the score itself is not adjusted.
- **Implementation effort.** A more carefully engineered harness will outperform a hasty one. This is part of the benchmark's value: it tells you which engineering investments paid off.

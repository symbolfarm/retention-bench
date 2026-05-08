# Clear Topology

The number of clears is the headline axis, but it is not the only knob. This document enumerates the topology dimensions that v1 tasks should be able to vary, even if defaults are conservative.

## Headline axis: `N`

`N` is the number of clears in a run. It is the parameter that defines the retention curve. Default: vary `N` from `0` to `S - 1` (between-stage clears for an `S`-stage task), reporting the curve.

## Clear placement

Where in the task the clears happen.

- **Uniform between-stage:** one clear between each pair of stages. The default and the cleanest case.
- **Clustered:** multiple clears between two adjacent stages. Tests whether back-to-back restarts cause additional damage beyond a single restart.
- **Adversarial:** clears placed right before high-value moments (the final synthesis, the patch-application step). Tests worst-case behaviour under deliberate stress.
- **Mid-stage:** clears within a single stage. Adversarial; only legal when the task explicitly supports it. Stresses fine-grained checkpointing.

Default for v1: **uniform between-stage.** Adversarial and mid-stage placements are flagged as stress variants.

## Clear awareness

Whether the SUT knows about clears.

- **Aware-precise (default):** SUT is told exactly how many clears remain and when they occur.
- **Aware-coarse:** SUT is told that clears will happen but not exactly when or how many. More realistic; harder.
- **Blind:** SUT is told nothing. Most realistic; hardest.

Default: **aware-precise.** Blind is a supported variant.

## Information geometry

How much novel, non-redundant information the SUT must carry across each clear.

This is independent of token count. A 100k-token chapter heavy on atmosphere may demand less memory bandwidth than a 20k-token chapter introducing 40 named entities and three plot threads. Tasks should annotate per-stage information density to allow controlled comparison.

In v1, this is a **reported metadata field** rather than a controlled parameter. v2 may extend to procedural generation that varies information density independently of length.

## Distractor pressure

Across clears, how much irrelevant information has accumulated.

Stages can include irrelevant or low-value content interleaved with high-value content. Memory systems that hoard indiscriminately fail under high distractor pressure; systems that prioritise pass.

Tasks should specify distractor levels (none, low, high) where it is meaningful to do so. v1 default: **as found in the source material**, with annotation.

## Retroactive relevance

Some post-clear tasks should require information that, at the time it was introduced, did not look important.

This stresses whether memory systems capture broadly or narrowly. A system that only saves "what seemed relevant to the current stage's task" will fail retroactively-relevant questions; one that saves more generously will pass but pay a retrieval cost later.

This tension is fundamental and should be made visible in the curves. Tasks should include questions of both types (concurrently-relevant and retroactively-relevant) and report scores broken down by type.

## Inter-clear contamination

Whether tasks in session `K+1` can require synthesising information from sessions `1` and `K` (long-range), or only from the immediately preceding session (local).

Long-range dependencies stress whether memory is a flat bag or whether structural / relational information survives. Local dependencies test the basic clear-and-recover loop.

V1 task tracks should include both. The book-episodic track naturally includes long-range (final-stage thematic questions); the codebase track naturally includes both.

## Interaction with clear-blind mode

When awareness is set to blind, retroactively-relevant questions and long-range dependencies are particularly punishing — the SUT cannot prepare for them. This is the intended stiffness of the blind mode and should be reported as part of the variant's signature, not avoided.

## Defaults summary for v1

| Dimension | v1 Default |
|---|---|
| `N` range | 0 to `S - 1` |
| Clear placement | uniform between-stage |
| Awareness | aware-precise |
| Information geometry | reported, not controlled |
| Distractor pressure | as found |
| Retroactive relevance | included in question mix |
| Inter-clear range | both local and long-range |

Variants of all of these are supported and should be runnable, but the default configuration is what produces comparable scores across SUTs and across the leaderboard.

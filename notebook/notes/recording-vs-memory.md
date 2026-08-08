---
status: live
tags: [theory, messaging, episodic, semantic, reconstruction]
tasks: []
---

# Recording vs memory

**A recording is verbatim, retrieved unchanged, and complete. A memory has been
re-represented — stored in a form other than the one it arrived in, and one that
supports queries the arrival form does not — which is why it composes.**

> **Correction (2026-08-08).** This previously read "compressed into a structure
> — which is why it composes, and why it is lossy". That conflated three things.
> **Lossiness** is a frequent *symptom* of re-representation, not its definition:
> random deletion is lossy and structures nothing. **Compression** is one reliable
> *cause*, not the definition: lossless compression removes redundancy while
> producing nothing queryable, and a growing semantic index re-represents without
> shrinking at all. The load-bearing property is re-representation. This matters
> because the project's own claim is about memory that **expands** — an instrument
> built on "compression forces structure" would be in tension with its own thesis,
> and could accidentally require that memory shrink.

This is the distinction the project's public claim now rests on. It replaced
"storage is not memory" (2026-08-02), which was wrong in a way worth recording:
it asserted a category difference between a store and a memory that we don't
actually believe. Storage *is* a kind of memory. The question is what happened to
the content after it was stored.

## The three positions

| | what persists | where it abstracts | consequence |
|---|---|---|---|
| In-context learning | nothing | query time, richly | the abstraction dies with the process |
| Retrieval / notes | a recording | query time, over a retrieved subset | re-derived every session, from a subset |
| Consolidation | the abstraction | write time | kept |

The middle row's limitation is **structural**: retrieval selects by query, so a
system cannot abstract over what it did not retrieve, and a question whose answer
is a property of the entire set has no query that surfaces it. This is the
specific reason to expect the aggregation rung to be hard for retrieval, and it
costs us nothing — it doesn't require denying in-context learning any power.

## The ICL correction (matters — we had this wrong)

Both README and ROADMAP previously said *"in-context learning produces access
without integration."* **That is false.** Within a context window transformers
integrate richly: attention composes over the whole window, and a model shown
instances of a rule induces it and applies it to a held-out input. That is
literally abstraction over episodes.

The claim survives only when moved from *whether* abstraction happens to **where
it goes**: computed at query time, discarded with the process, what persists is
the token sequence that produced it.

This is a better claim than the one it replaced. It is honest about the
transformer (so it can't be dismissed on a point of fact), it fits the
volatile/persistent × episodic/semantic 2×2 below, and it yields the structural
aggregation argument above.

Casualty: the line *"retrieval is in-context learning with a bigger drawer."*
Good line, but it asserted exactly the thing being corrected — retrieval adds
access *and* re-derived integration, just transiently and over a subset. Retired
rather than repaired.

## Why the axes look like one axis

Episodic/semantic is a **content** distinction (Tulving): episodic = memory for a
particular event, indexed to when and where; semantic = general fact, stripped of
the episode that taught it. Persistence is a **durability** distinction. They are
orthogonal:

| | volatile | persistent |
|---|---|---|
| **episodic** | conversation history in-context | a log, a journal, a transcript |
| **semantic** | abstraction derived in-context, then discarded | weights; a notes file of general rules |

For a frontier LLM three cells are nearly empty in practice — the only episodic
memory it has *is* the context window, which is also the only volatile store, and
the only persistent store *is* the weights, which are semantic. So
episodic≈volatile and semantic≈persistent, and the two axes collapse into one.

**That collapse is a contingent fact about current architectures, not a
conceptual truth.** Prying the axes apart is part of what this instrument is for,
and it is why the slogan has two clauses rather than one.

## Provenance: human memory is reconstructive

Where the distinction came from (Toby's introspection: recalling semantic facts
about a day without recalling the events; encoding feels roughly simultaneous).
The supporting literature, **noted as pointers — not yet read properly, no
reference notes exist yet**:

- **Bartlett (1932)**, *War of the Ghosts* — recall reshapes a story toward the
  recaller's schemas across retellings. Remembering as reconstruction.
- **Loftus**, misinformation effect — retrieval itself rewrites the trace.
- **Schacter & Addis**, constructive episodic simulation hypothesis — episodic
  memory is reconstructive *because* it shares machinery with imagining the
  future. Supporting result: **Hassabis et al. (2007, PNAS)** — hippocampal
  amnesiacs cannot construct novel *imagined* scenes either.
- **Brainerd & Reyna**, fuzzy-trace theory — verbatim and gist traces encoded **in
  parallel**, not gist-derived-from-verbatim; verbatim decays faster. This is the
  one that matches the introspection directly.
- **McClelland, McNaughton & O'Reilly (1995)**, Complementary Learning Systems —
  the standard fast-episodic / slow-structured two-system account.

Two consequences we act on:

**1. Episodic→semantic is not a strict pipeline.** Fuzzy-trace says gist can be
laid down alongside the episode rather than extracted from it later. So *abstraction
at write time is a legitimate mechanism, not cheating* — which matters for
constructive-retention. Documents must not imply a mandatory store-then-abstract
order. It also lands directly on ROADMAP open question 3 (the anticipation gap):
abstracting at encoding means choosing what to keep before knowing the question.

**2. Argue functionally, not biologically.** Discovery vs justification. Human
memory architecture is the best available prior for *where to look* — it is the one
agreed existence proof of general intelligence, and reasoning from it is what
produced this whole note. What does not survive a skeptic is the same fact used as
*evidence*: "humans reconstruct, therefore a system that doesn't can't understand."
The functional version costs nothing and stays falsifiable: **a store that keeps
only the arrival form, under no pressure to re-represent, has no route to the
upper rungs.** (Corrected 2026-08-08 — see the header.)

## Related

- [The episodic→semantic axis](episodic-semantic-axis.md) — what the probe ladder
  measures, and the profile-across-rungs reading that follows from this note.
- [ADUS mapping](adus-mapping.md) — the channel taxonomy this specialises.

## Changelog

- 2026-08-02: created. Supersedes the "storage is not memory" framing in README
  and ROADMAP; records the ICL correction and the reconstruction provenance.
- 2026-08-08: **compression → re-representation.** Compression and lossiness were
  standing in for the load-bearing property; see the correction in the header.
  Propagated to `README.md` and `docs/ROADMAP.md`. Raised by Toby.

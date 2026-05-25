# B2 Naive-RAG reference SUT

**Priority:** medium
**Blocked by:** nothing (B1 landed; harness path is regression-protected)
**Touches:** `suts/naive_rag/`, `tests/fixtures/`, `tests/test_naive_rag_*.py`

## Context

B2 is the third reference SUT, completing the baseline trio (no-state →
notes-llm → naive-RAG). Per decision #11 (resolved B): naive-RAG is "the
thing to beat" — having it as a reference makes any new memory
architecture's value immediately legible. Per decision #5 (resolved C,
with B as load-bearing): naive-RAG's vector index lives in `DIR`; the
embedding model is SUT "code" and doesn't count toward storage.

This is the first SUT whose `DIR` content is *not* freeform text — it's
a chunked corpus + a vector index. Sibling to notes-llm but stylistically
different: where notes-llm distills, naive-RAG preserves and retrieves.

The design space should be jointly scoped with Toby before any code is
written (same pattern as B1). The "Decisions already made" section
below is a starting point — most details still need to be locked.

## Goal

A runnable reference SUT under `suts/naive_rag/` that on READ events
chunks the chapter text, embeds the chunks, and appends them to a
vector index in `DIR`. On QUIZ events it embeds the question, retrieves
top-k chunks from the index, and asks the LLM to answer using those
chunks as context. Same packaging shape as no-state / notes-llm. Drives
end-to-end through the harness, produces a retention curve.

## Acceptance criteria

- [ ] `suts/naive_rag/` package: `sut-manifest.json`,
      `naive_rag/__main__.py`, `pyproject.toml`, `README.md`.
- [ ] On READ: chunk the chapter, embed each chunk, append chunks +
      embeddings to a vector index file in `DIR` (e.g.
      `DIR/index.{jsonl,npz,sqlite}` — locked at scoping time).
- [ ] On QUIZ: embed each question, retrieve top-k chunks from the
      index, call the LLM with question + retrieved chunks, parse
      `<ANSWER>` tags into structured `answers` list per
      `docs/sut-interface.md`.
- [ ] Resource fields emitted on every LLM-and-embedding event reply
      (`tokens_in/out`, `api_call_count`, `embedding_call_count` if
      relevant, `model_id`).
- [ ] Index format survives `RESET` and round-trips cleanly.
- [ ] Test fixture exercising multi-chapter retrieval + RESET
      (probably reuses `tests/fixtures/two_chapter.yaml` or a new
      sibling).
- [ ] Integration test against the fake-anthropic shim (extend the
      B10 pattern). If embedding API is also Anthropic, the shim will
      need to grow embedding support; if not, second shim or
      out-of-shim path required (see open questions).
- [ ] All existing tests still pass.

## Open questions to scope with Toby

1. **Embedding provider.** Anthropic doesn't ship an embedding API
   (as of 2026-05). Options: (a) hash-based / TF-IDF / BM25 (no
   external embeddings at all — "naive-naive" RAG); (b) Voyage AI
   (Anthropic-recommended embedder); (c) OpenAI embeddings; (d)
   sentence-transformers locally. Each has trade-offs for repro,
   network deps, dev-container fit, and what counts as "SUT code"
   vs DIR content.

2. **Chunking strategy.** Fixed token window with overlap? Sentence-
   based? Paragraph-based? Recursive (LangChain-style)? Naive-RAG
   should be naive — but "naive" still admits multiple defensible
   defaults. Pick one and document.

3. **Index format.** Plain JSONL (chunk text + embedding as list of
   floats) is simple and inspectable. NPZ / SQLite faster but
   binary. Per docs/sut-interface.md, `DIR` artifacts may be audited
   post-hoc — inspectability has weight.

4. **Top-k retrieval.** k=3? k=5? Distance metric (cosine, dot,
   euclid)? Whether to threshold on similarity score?

5. **Fake-shim strategy for embeddings.** If we use Voyage/OpenAI,
   the test shim needs embedding support too — or we use BM25/TF-IDF
   for the integration test and the real embedder only for live runs.

6. **Multi-chapter context strategy.** If question is about chapter
   1 and chapter 5 was just READ, top-k might surface only ch-5
   chunks. Worth thinking about whether retention measurement
   accidentally measures recency bias of the embedder.

## Relevant files

- `suts/notes_llm/notes_llm/__main__.py` — closest template (DIR
  persistence + LLM call patterns).
- `suts/no_state/no_state/__main__.py` — bare-bones SUT shape.
- `docs/sut-interface.md` — wire contract.
- `docs/decisions-checklist.md` decisions #5, #11 — naive-RAG's
  intended role.
- `tests/fake_anthropic_shim/anthropic.py` — extend for embeddings or
  decide on out-of-shim path.
- `tests/test_notes_llm_fake_anthropic.py` — pattern for the test.

## Out of scope

- Hybrid retrieval (sparse + dense) — sophisticated, not naive.
- Re-ranking — sophisticated, not naive.
- Query expansion / HyDE — sophisticated, not naive.
- Index compaction / pruning across RESETs — premature; let the
  index grow.
- LLM-judge scorer (B3) — separate task.
- Docker packaging (B4) — separate task.
- Generic LLM-backend abstraction (B9) — separate task.

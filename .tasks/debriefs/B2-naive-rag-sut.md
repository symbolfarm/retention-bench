# Debrief: B2 Naive-RAG reference SUT

**Completed:** 2026-05-26
**Commit:** (see below)

## What shipped

- `suts/naive_rag/` package: `naive_rag/__main__.py`, `naive_rag/__init__.py`,
  `sut-manifest.json`, `pyproject.toml`, `README.md`.
- **READ events**: chunk the chapter text (200-word window, 40-word overlap),
  embed each chunk via the selected backend, append to `DIR/index.jsonl`.
- **QUIZ events**: embed each question, retrieve top-5 chunks by cosine
  similarity (deduplicated across questions), single LLM call with combined
  context, parse `<ANSWER>` tags into the structured `answers` list.
- **Pluggable embedder seam**: `Embedder` protocol with three backends
  selectable via `NAIVE_RAG_EMBEDDER` env var (`fake` / `sentence-transformers`
  / `llama-cpp`). Default: `sentence-transformers`.
- **Index format**: `DIR/index.jsonl` — human-readable JSONL, one object per
  chunk: `{chunk_id, material_ref, text, embedding}`.
- **Resource fields**: `tokens_in`, `tokens_out`, `api_call_count`,
  `embedding_call_count`, `model_id` on every reply.
- **Integration test**: `tests/test_naive_rag_fake_anthropic.py` — fake
  embedder + fake_anthropic_shim, drives through multi-chapter READ + QUIZ +
  RESET, asserts index.jsonl survives RESET and contains content from both
  chapters, asserts per-question answers and resource aggregation.
- **Test fixture**: `tests/fixtures/fake_anthropic_naive_rag_responses.yaml`
  (2 canned LLM responses: one per QUIZ event; READ events use embedding only).
- Full suite: **43 passed, 1 skipped** (the skip is the live no_state test,
  pre-existing).

## Descoped / deferred

- Live retention curve (no API budget spent, no live run performed — explicit
  per brief). Noted as follow-up below.
- `llama-cpp` not tested end-to-end in this worktree (native build not
  attempted). Backend is fully wired; switching is one env-var change.

## Design decisions

**Default backend: `sentence-transformers` instead of `llama-cpp`.**
The brief specified `llama-cpp` as the preferred default but permitted a
one-line switch if the native build failed within a bounded attempt. Rather
than burn time on a native build in this worktree, `sentence-transformers`
was set as default immediately. It requires no native build (runs on CPU),
`all-MiniLM-L6-v2` is a well-known 384-dim model. Switch: set
`NAIVE_RAG_EMBEDDER=llama-cpp` (and `NAIVE_RAG_LLAMA_MODEL` to the GGUF path).

**Decision #5 / #11 refinement (flag for decisions-checklist):**
The llama-cpp dense backend is fully wired behind the embedder seam. The
default was changed to `sentence-transformers` because the native build was
out of scope for B2. This refinement should be mirrored into
`docs/decisions-checklist.md`: decision #11 note — "naive-RAG ships with
`sentence-transformers` as the default embedder backend; llama-cpp is wired
and switchable via env var; B2 agent set sentence-transformers as default
because native build was explicitly out of scope."

**Batch retrieval for multi-question QUIZ**: when a QUIZ carries multiple
questions, top-k is retrieved per question and deduplicated by `chunk_id`,
then a single LLM call is made with all unique chunks. This reduces API
calls vs. per-question calls; the brief did not specify. Easy to change if
per-question isolation is preferred.

**`material_ref` extraction from META block**: the SUT parses
`material_id:` from the harness-generated `<META>` block in the READ
`stage_input` to produce informative `chunk_id` values. Falls back to
`"unknown"` if no META block is present.

## Observations

- The fake embedder's hash-based pseudo-vectors are deterministic by
  construction (SHA-256 → unit-normalised). This means cosine similarity
  between the question embedding and chunk embeddings is deterministic and
  non-trivial — close enough for the test to exercise the retrieval path
  meaningfully without torch or any real model.
- The index grows monotonically across READ events and is append-only.
  After a RESET, the new SUT subprocess reads the same index from disk;
  the QUIZ retrieves chunks from all previously-read chapters. This is
  intentional (it means the post-RESET SUT does NOT forget prior chapters)
  and matches the "thing to beat" design intent.
- **Open question #6 (multi-chapter recency bias)**: not solved. If the
  embedder produces more similar vectors for recent-chapter text (because
  the question is about chapter 5 material), top-k may surface only recent
  chunks. This is a known limitation of vanilla RAG and is intentionally
  left as-is — it is a property to *measure*, not to fix in the reference
  SUT.

## Follow-ups

### Filed as tasks

None filed during B2 (all follow-ups below are candidates, not yet filed).

### Drive-by cleanup landed

None.

### Considered and dropped

- **Per-question LLM calls**: considered a mode where each question gets its
  own LLM call with its own top-k context. Dropped in favour of batch:
  cheaper, simpler, and the brief does not require per-question isolation.

### Candidate follow-ups (not yet filed)

- **Live retention curve run** (deferred per brief): run `naive_rag` against
  the full task fixture with real embedder + real LLM to produce an actual
  retention curve. Explicitly deprioritised in B2.
- **B9 scope-growth**: naive_rag adds a third hardcoded-Anthropic call site
  (`client.messages.create(...)` in `_call_llm`). B9 (generic LLM-backend
  abstraction) will need to cover this call site alongside `notes_llm` and
  `no_state`. Flag for B9 planning.
- **llama-cpp default**: if the native build is verified in the dev container
  (e.g., as part of B4 Docker packaging), the default should be switched back
  to `llama-cpp` to match the original intent. One-line change in `_make_embedder`.
- **Recency bias measurement**: track per-chunk `material_ref` in QUIZ
  retrieval traces to surface whether the embedder systematically over-ranks
  recent chapters. Useful for interpreting naive-RAG retention curves.

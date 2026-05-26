# naive-rag SUT

Naive-RAG reference SUT for retention-bench. The "thing to beat" baseline:
on `READ` events, chunks the chapter text and stores embeddings in a vector
index under `DIR`; on `QUIZ` events, embeds each question, retrieves the
top-k most-similar chunks, and asks the LLM to answer.

## Chunking parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| `CHUNK_SIZE` | 200 words | Target words per chunk |
| `CHUNK_OVERLAP` | 40 words | Words shared between consecutive chunks |
| Strategy | Fixed-size word window | No semantic/recursive splitting — intentionally naive |

Word-window chunking: words are split on whitespace. Chunks slide with
stride `CHUNK_SIZE - CHUNK_OVERLAP = 160` words; the final chunk may be
shorter.

## Index format

`DIR/index.jsonl` — one JSON object per line, human-readable and auditable:

```json
{"chunk_id": "chapter_one_0", "material_ref": "chapter_one", "text": "...", "embedding": [0.12, -0.34, ...]}
```

| Field | Type | Notes |
|-------|------|-------|
| `chunk_id` | string | `{material_ref}_{sequence_number}` |
| `material_ref` | string | The `material_id` from the harness `META` block |
| `text` | string | Verbatim chunk text |
| `embedding` | list[float] | Unit-normalised embedding vector |

The index is append-only across `READ` events. It survives `RESET` (because
`DIR` persists). After `RESET`, a new SUT subprocess reads the index from
disk to answer questions about previously-read material.

## Retrieval

- Metric: cosine similarity (vectors are pre-normalised to unit length)
- `TOP_K = 5` chunks retrieved per question
- When a QUIZ has multiple questions, top-k is retrieved for each and
  deduplicated by `chunk_id`; all unique chunks are passed to a single LLM
  call

## Embedder backends

Selected by the `NAIVE_RAG_EMBEDDER` environment variable:

| Value | Backend | Deps | Notes |
|-------|---------|------|-------|
| `fake` | Hash-based pseudo-vectors | None | Deterministic, offline, test-only |
| `sentence-transformers` | `all-MiniLM-L6-v2` | `sentence-transformers` (pulls torch) | **Default** |
| `llama-cpp` | GGUF model via `llama-cpp-python` | `llama-cpp-python` + model file | No torch; needs native build |

**Default backend: `sentence-transformers`.**

`llama-cpp` was the originally-preferred default (no-torch, smaller runtime)
but was not set as default because getting the native `llama-cpp-python` build
working in the dev container requires a bounded native-build step that was
explicitly out of scope for B2. `sentence-transformers` is a fully wired
alternative that works on CPU without a native build. The switch is a one-line
env-var change: `NAIVE_RAG_EMBEDDER=llama-cpp`.

For `llama-cpp`, set `NAIVE_RAG_LLAMA_MODEL` to the path of a GGUF embedding
model (default: `bge-small-en-v1.5-q8_0.gguf` in the current directory).

## LLM model

The LLM used for answer generation is set by `NAIVE_RAG_MODEL`
(default: `claude-haiku-4-5-20251001`). The Anthropic client is
instantiated directly from `ANTHROPIC_API_KEY` — same idiom as
`notes_llm` and `no_state` (B9 will unify these call sites).

## Resource fields

Every response includes:

| Field | Notes |
|-------|-------|
| `embedding_call_count` | Number of embed() calls made |
| `model_id` | LLM model id on QUIZ; embedder model id on READ |
| `tokens_in` / `tokens_out` | LLM token usage (QUIZ events only) |
| `api_call_count` | LLM API calls (1 per QUIZ event) |

## Installation

```bash
# Bare install (fake embedder only — for tests):
pip install -e suts/naive_rag/

# With sentence-transformers:
pip install -e "suts/naive_rag/[sentence-transformers]"

# With llama-cpp:
pip install -e "suts/naive_rag/[llama-cpp]"
```

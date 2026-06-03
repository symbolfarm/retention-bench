"""Naive-RAG reference SUT for retention-bench.

Reads JSONL events from stdin (per docs/sut-interface.md), responds on stdout.
On READ: chunks the chapter text, embeds each chunk, appends to DIR/index.jsonl.
On QUIZ: embeds the question, retrieves top-k chunks by cosine similarity,
         calls the LLM with question + chunks, parses <ANSWER> tags into the
         structured answers list.

Index format: DIR/index.jsonl — one JSON object per line:
  {"chunk_id": str, "material_ref": str, "text": str, "embedding": [float...]}

Chunking: fixed-size word window, CHUNK_SIZE=200 words, CHUNK_OVERLAP=40 words.
Retrieval: cosine similarity, TOP_K=5 chunks.
LLM call shape: matches notes_llm / no_state idiom exactly — shared
OpenAI-compatible (OpenRouter) client idiom since B9.

Embedder backend selected by NAIVE_RAG_EMBEDDER env var:
  fake               — deterministic hash-based pseudo-vectors (default for tests)
  sentence-transformers — real dense retrieval via all-MiniLM-L6-v2
  llama-cpp          — real dense retrieval via llama-cpp-python + GGUF model

Default backend: sentence-transformers (see README for rationale on why
llama-cpp was not set as default).

Wire contract: QUIZ replies carry a structured `answers` list of
{"id": <qid>, "text": <answer>}. The model is asked to emit <ANSWER>-tagged
output; that's our internal convention for extracting per-question answers.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Iterable, Protocol

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
MAX_TOKENS = 4096

# Chunking parameters (documented in README)
CHUNK_SIZE = 200       # words per chunk
CHUNK_OVERLAP = 40     # words of overlap between consecutive chunks
TOP_K = 5              # number of chunks to retrieve per question

INDEX_FILENAME = "index.jsonl"

# Fake embedder parameters
FAKE_EMBED_DIM = 64

# ---------------------------------------------------------------------------
# Embedder protocol + backends
# ---------------------------------------------------------------------------


class Embedder(Protocol):
    """Interface every embedder backend must satisfy."""

    @property
    def backend_name(self) -> str:
        """Short identifier, e.g. 'fake', 'sentence-transformers', 'llama-cpp'."""
        ...

    @property
    def model_id(self) -> str:
        """Model identifier string (name or path)."""
        ...

    def embed(self, text: str) -> list[float]:
        """Return a fixed-length embedding vector for text."""
        ...


class FakeEmbedder:
    """Deterministic hash-based pseudo-embedder. No deps. Used in tests."""

    backend_name = "fake"
    model_id = f"fake-hash-dim{FAKE_EMBED_DIM}"

    def embed(self, text: str) -> list[float]:
        """Hash the text into a stable unit vector of FAKE_EMBED_DIM floats."""
        import hashlib
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Expand bytes into FAKE_EMBED_DIM values deterministically
        raw: list[float] = []
        for i in range(FAKE_EMBED_DIM):
            byte_val = h[i % len(h)]
            # Mix index into value for independence across dimensions
            mixed = (byte_val ^ (i * 37)) & 0xFF
            raw.append(float(mixed) - 127.5)
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [x / norm for x in raw]


class SentenceTransformersEmbedder:
    """Dense embedder via sentence-transformers all-MiniLM-L6-v2."""

    backend_name = "sentence-transformers"
    _MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Install with: pip install sentence-transformers"
            )
        self._model = SentenceTransformer(self._MODEL_NAME)

    @property
    def model_id(self) -> str:
        return self._MODEL_NAME

    def embed(self, text: str) -> list[float]:
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.tolist()


class LlamaCppEmbedder:
    """Dense embedder via llama-cpp-python + a GGUF embedding model."""

    backend_name = "llama-cpp"

    def __init__(self) -> None:
        model_path = os.environ.get(
            "NAIVE_RAG_LLAMA_MODEL",
            "bge-small-en-v1.5-q8_0.gguf",
        )
        try:
            from llama_cpp import Llama  # type: ignore
        except ImportError:
            raise ImportError(
                "llama-cpp-python is not installed. "
                "Install with: pip install llama-cpp-python"
            )
        self._model_path = model_path
        self._llama = Llama(model_path=model_path, embedding=True, verbose=False)

    @property
    def model_id(self) -> str:
        return self._model_path

    def embed(self, text: str) -> list[float]:
        result = self._llama.embed(text)
        # llama-cpp returns list[list[float]] for batch or list[float] for single
        if result and isinstance(result[0], list):
            vec = result[0]
        else:
            vec = result  # type: ignore[assignment]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


def _make_embedder() -> Embedder:
    """Instantiate the embedder backend selected by NAIVE_RAG_EMBEDDER."""
    backend = os.environ.get("NAIVE_RAG_EMBEDDER", "sentence-transformers").lower()
    if backend == "fake":
        return FakeEmbedder()
    if backend == "sentence-transformers":
        return SentenceTransformersEmbedder()
    if backend in ("llama-cpp", "llama_cpp"):
        return LlamaCppEmbedder()
    _die(
        f"Unknown NAIVE_RAG_EMBEDDER={backend!r}. "
        "Valid values: fake, sentence-transformers, llama-cpp",
        code=2,
    )


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def _chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into fixed-size word-window chunks with overlap.

    Returns a list of chunk strings. Each chunk is at most `chunk_size` words;
    consecutive chunks share `overlap` words from the end of the previous chunk.
    The final chunk may be shorter.
    """
    words = text.split()
    if not words:
        return []
    step = max(1, chunk_size - overlap)
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunk_words = words[start : start + chunk_size]
        chunks.append(" ".join(chunk_words))
        start += step
    return chunks


# ---------------------------------------------------------------------------
# Index I/O
# ---------------------------------------------------------------------------


def _index_path(cwd: Path) -> Path:
    return cwd / INDEX_FILENAME


def _append_to_index(
    index_file: Path,
    chunks: list[str],
    material_ref: str,
    embedder: Embedder,
) -> int:
    """Embed each chunk and append to JSONL index. Returns embedding call count."""
    # Count existing lines to generate unique chunk IDs
    start_id = 0
    if index_file.exists():
        with index_file.open("r", encoding="utf-8") as f:
            for _ in f:
                start_id += 1

    with index_file.open("a", encoding="utf-8") as f:
        for i, chunk in enumerate(chunks):
            embedding = embedder.embed(chunk)
            obj = {
                "chunk_id": f"{material_ref}_{start_id + i}",
                "material_ref": material_ref,
                "text": chunk,
                "embedding": embedding,
            }
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    return len(chunks)


def _load_index(index_file: Path) -> list[dict]:
    """Load all index entries. Returns empty list if file absent."""
    if not index_file.exists():
        return []
    entries = []
    with index_file.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two pre-normalised vectors."""
    if len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def _retrieve_top_k(
    query_embedding: list[float],
    entries: list[dict],
    k: int = TOP_K,
) -> list[dict]:
    """Return up to k entries sorted by descending cosine similarity."""
    scored = [
        (entry, _cosine_similarity(query_embedding, entry["embedding"]))
        for entry in entries
    ]
    scored.sort(key=lambda t: t[1], reverse=True)
    return [e for e, _ in scored[:k]]


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

_QUESTION_RE = re.compile(
    r'<QUESTION\s+id="([^"]+)">(.*?)</QUESTION>', re.DOTALL
)
_ANSWER_RE = re.compile(
    r'<ANSWER\s+id="([^"]+)">(.*?)</ANSWER>', re.DOTALL
)
_TEXT_RE = re.compile(r"<TEXT>\s*(.*?)\s*</TEXT>", re.DOTALL)
_META_RE = re.compile(r"<META>(.*?)</META>", re.DOTALL)


QUIZ_SYSTEM_PROMPT = (
    "You are a question-answering assistant for a retention benchmark. "
    "You will be shown retrieved context chunks from a knowledge base, "
    "followed by questions. Answer each question using only the provided "
    "context chunks.\n\n"
    "For each question, emit your answer wrapped in "
    '<ANSWER id="..."> ... </ANSWER> tags, reusing the question id verbatim. '
    "Emit one ANSWER block per question, in order, with nothing else around "
    "them. If the context does not contain the answer, write Unknown inside "
    "the tags."
)


def _parse_chapter(stage_input: str) -> tuple[str, str]:
    """Return (text, material_ref) from a READ stage_input."""
    text_m = _TEXT_RE.search(stage_input)
    text = text_m.group(1) if text_m else ""
    # Try to extract material_ref from META block
    meta_m = _META_RE.search(stage_input)
    material_ref = "unknown"
    if meta_m:
        meta_text = meta_m.group(1)
        for line in meta_text.splitlines():
            line = line.strip()
            if line.startswith("material_id:"):
                material_ref = line.split(":", 1)[1].strip()
                break
    return text, material_ref


def _parse_questions(stage_input: str) -> list[tuple[str, str]]:
    return [(q, t.strip()) for q, t in _QUESTION_RE.findall(stage_input)]


def _quiz_user_prompt(question_id: str, question_text: str, chunks: list[dict]) -> str:
    if chunks:
        context = "\n\n".join(
            f"[Chunk {i + 1} from {c['material_ref']}]\n{c['text']}"
            for i, c in enumerate(chunks)
        )
    else:
        context = "(no relevant context found in the index)"
    return (
        "Retrieved context chunks:\n"
        "<CONTEXT>\n"
        f"{context}\n"
        "</CONTEXT>\n\n"
        f'<QUESTION id="{question_id}">{question_text}</QUESTION>\n\n'
        'Answer the question. Wrap your answer as '
        f'<ANSWER id="{question_id}"> ... </ANSWER>.'
    )


def _quiz_user_prompt_batch(
    questions: list[tuple[str, str]],
    all_chunks: list[dict],
) -> str:
    """Build a single prompt for all questions with combined retrieved context."""
    if all_chunks:
        context = "\n\n".join(
            f"[Chunk {i + 1} from {c['material_ref']}]\n{c['text']}"
            for i, c in enumerate(all_chunks)
        )
    else:
        context = "(no relevant context found in the index)"
    q_block = "\n".join(
        f'<QUESTION id="{q}">{t}</QUESTION>' for q, t in questions
    )
    return (
        "Retrieved context chunks:\n"
        "<CONTEXT>\n"
        f"{context}\n"
        "</CONTEXT>\n\n"
        "Questions:\n"
        f"{q_block}\n\n"
        'Answer each question. Wrap each answer as <ANSWER id="..."> ... </ANSWER>.'
    )


def _extract_answers(model_text: str) -> list[dict]:
    out: list[dict] = []
    for m in _ANSWER_RE.finditer(model_text):
        qid, body = m.group(1), m.group(2).strip()
        out.append({"id": qid, "text": body})
    return out


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------


def _call_llm(client, model: str, system: str, user: str):
    resp = client.chat.completions.create(
        model=model,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = resp.choices[0].message.content or ""
    usage = getattr(resp, "usage", None)
    tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
    tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0
    return text, tokens_in, tokens_out


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------


def _handle_read(
    embedder: Embedder,
    index_file: Path,
    event: dict,
) -> dict:
    eid = event["event_id"]
    text, material_ref = _parse_chapter(event.get("stage_input", ""))
    chunks = _chunk_text(text)
    if not chunks:
        return {
            "event_id": eid,
            "stage_output": "",
            "embedding_call_count": 0,
            "notes": "empty chapter text — nothing indexed",
        }
    embed_calls = _append_to_index(index_file, chunks, material_ref, embedder)
    return {
        "event_id": eid,
        "stage_output": "",
        "embedding_call_count": embed_calls,
        "model_id": embedder.model_id,
        "notes": (
            f"indexed {len(chunks)} chunks from {material_ref!r} "
            f"(embedder: {embedder.backend_name})"
        ),
    }


def _handle_quiz(
    client,
    model: str,
    embedder: Embedder,
    index_file: Path,
    event: dict,
) -> dict:
    eid = event["event_id"]
    questions = _parse_questions(event.get("stage_input", ""))
    if not questions:
        return {
            "event_id": eid,
            "answers": [],
            "notes": "no <QUESTION> tags found in stage_input",
        }

    entries = _load_index(index_file)

    # Embed all questions and retrieve top-k for each; deduplicate by chunk_id
    # to avoid repeating the same chunk in the context window.
    seen_chunk_ids: set[str] = set()
    combined_chunks: list[dict] = []
    embed_calls = 0

    for _qid, qtext in questions:
        q_emb = embedder.embed(qtext)
        embed_calls += 1
        top = _retrieve_top_k(q_emb, entries, k=TOP_K)
        for chunk in top:
            cid = chunk["chunk_id"]
            if cid not in seen_chunk_ids:
                seen_chunk_ids.add(cid)
                combined_chunks.append(chunk)

    # Single LLM call for all questions with the combined context
    user_prompt = _quiz_user_prompt_batch(questions, combined_chunks)
    text, tokens_in, tokens_out = _call_llm(client, model, QUIZ_SYSTEM_PROMPT, user_prompt)

    return {
        "event_id": eid,
        "answers": _extract_answers(text),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "api_call_count": 1,
        "embedding_call_count": embed_calls,
        "model_id": model,
        "notes": (
            f"retrieved {len(combined_chunks)} unique chunks for "
            f"{len(questions)} question(s); embedder={embedder.backend_name}"
        ),
    }


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _die(msg: str, code: int = 1) -> None:
    print(f"naive-rag SUT: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def _iter_events(stream: Iterable[str]):
    for line in stream:
        line = line.strip()
        if line:
            yield json.loads(line)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        _die("OPENROUTER_API_KEY is not set; refusing to start.", code=2)

    try:
        import openai  # type: ignore
    except ImportError:
        _die("`openai` package is not installed (pip install openai).", code=2)

    model = os.environ.get("NAIVE_RAG_MODEL", DEFAULT_MODEL)
    base_url = os.environ.get("RETENTION_BENCH_BASE_URL", DEFAULT_BASE_URL)
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    embedder = _make_embedder()
    index_file = _index_path(Path.cwd())

    for event in _iter_events(sys.stdin):
        eid = event.get("event_id", "")
        etype = event.get("event_type", "")
        if etype == "READ":
            response = _handle_read(embedder, index_file, event)
        elif etype == "QUIZ":
            response = _handle_quiz(client, model, embedder, index_file, event)
        else:
            response = {
                "event_id": eid,
                "stage_output": "",
                "notes": f"unknown event_type: {etype}",
            }
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()

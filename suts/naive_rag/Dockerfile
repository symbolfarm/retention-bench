# naive_rag reference SUT image.
#
# Extends the shared API base (openai SDK pre-installed). Build the base
# first, then this image from the SUT directory:
#
#   docker build -f suts/sut-python-base.Dockerfile \
#     -t retention-bench/sut-python-base:0.1 suts/
#   docker build -t retention-bench/sut-naive-rag:0.1 suts/naive_rag/
#
# At runtime the harness runs `docker run -w /dir … <image> python -m naive_rag`
# (entrypoint from sut-manifest.json); DIR is bind-mounted at /dir.
#
# Embedder backend (decided 2026-05-30, task B4b):
#   This image bakes in the `sentence-transformers` backend (the SUT's existing
#   default). The originally-floated flip to a llama-cpp default was NOT done
#   here: llama-cpp-python needs a native (gcc/cmake) build step *and* a GGUF
#   model file that isn't in the repo, both of which fight a clean, reproducible
#   image build. sentence-transformers installs from wheels (pulling CPU torch),
#   needs no native toolchain, and its all-MiniLM-L6-v2 model is fetched on first
#   use. The flip stays a one-line env change (NAIVE_RAG_EMBEDDER=llama-cpp) for
#   anyone who provides the toolchain + model; it is not the image default.
#
# NOTE: sentence-transformers pulls in (CPU) torch, so this image is materially
# heavier than no_state/notes_llm despite sharing the slim base. That is an
# accepted cost for a working real-retrieval default; the API trio's *base*
# layer is still shared and slim.
FROM retention-bench/sut-python-base:0.1

WORKDIR /opt/sut

# Install the SUT with the sentence-transformers extra. openai comes from
# the base; the extra adds sentence-transformers (+ CPU torch). We do NOT pass
# --no-deps here because the extra brings real transitive dependencies that
# must resolve.
COPY pyproject.toml ./
COPY naive_rag/ naive_rag/
RUN pip install ".[sentence-transformers]"

# Bake the embedding model into the image so the container runs offline at
# QUIZ/READ time (no first-use network fetch inside the sandboxed run). If this
# pre-fetch is undesirable, drop this line and accept a first-use download.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

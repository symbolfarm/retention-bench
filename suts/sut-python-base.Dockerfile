# Shared slim base: python + the openai SDK, built and cached once.
#
# Used directly by the API-based reference SUT (notes_llm), and as the base
# for sut-torch-cpu-base (which the constructive SUT builds on).
#
# Build once, tag as retention-bench/sut-python-base:0.1, then the child
# Dockerfiles `FROM` it. This keeps the common layer (python + the openai
# SDK) built and cached a single time.
#
#   docker build -f suts/sut-python-base.Dockerfile \
#     -t retention-bench/sut-python-base:0.1 suts/
#
# Do NOT add torch / sentence-transformers here — the constructive SUT
# (and any heavy embedder backend) gets its own base so this one stays
# slim (decided 2026-05-30).

# Pinned digest-free but version-pinned base; python:3.11-slim is the
# decided base image for the API SUT.
FROM python:3.11-slim

# Fail fast, no .pyc clutter, unbuffered stdio (the wire contract needs
# stdout flushed per response — see docs/sut-interface.md "What the SUT
# MUST do" #3).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# The shared runtime dependency for the API SUT. Pinned to match the floor
# declared in the notes_llm pyproject.toml (openai>=1.40.0). notes_llm calls
# an OpenAI-compatible endpoint (OpenRouter by default). Installed here so
# images built on this base share the layer.
RUN pip install "openai>=1.40.0"

# Child images set their own WORKDIR for the build copy, then the harness
# overrides the runtime workdir to /dir (the bind-mounted DIR) via
# `docker run -w /dir`. Nothing to do here.

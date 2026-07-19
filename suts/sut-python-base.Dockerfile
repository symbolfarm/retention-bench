# Shared slim base for the three API-only reference SUTs
# (no_state, notes_llm, naive_rag).
#
# Build once, tag as retention-bench/sut-python-base:0.1, then the three
# API SUT Dockerfiles `FROM` it. This keeps the common layer (python +
# the openai SDK) built and cached a single time.
#
#   docker build -f suts/sut-python-base.Dockerfile \
#     -t retention-bench/sut-python-base:0.1 suts/
#
# Do NOT add torch / sentence-transformers here — the constructive SUT
# (and any heavy embedder backend) gets its own base so this one stays
# slim (decided 2026-05-30).

# Pinned digest-free but version-pinned base; python:3.11-slim is the
# decided base image for the API trio.
FROM python:3.11-slim

# Fail fast, no .pyc clutter, unbuffered stdio (the wire contract needs
# stdout flushed per response — see docs/sut-interface.md "What the SUT
# MUST do" #3).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# The one shared runtime dependency for the API SUTs. Pinned to match the
# floor declared across the SUT pyproject.toml files (openai>=1.40.0). The
# SUTs call an OpenAI-compatible endpoint (OpenRouter by default).
# Installed here so the three child images share this layer.
RUN pip install "openai>=1.40.0"

# Child images set their own WORKDIR for the build copy, then the harness
# overrides the runtime workdir to /dir (the bind-mounted DIR) via
# `docker run -w /dir`. Nothing to do here.

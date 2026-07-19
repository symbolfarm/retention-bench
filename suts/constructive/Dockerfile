# constructive (train-and-grow) reference SUT image.
#
# Extends the CPU-only torch base (NOT the slim API base — torch is heavy and
# only this SUT needs it; decided 2026-05-30). Build the torch base
# first, then this image from the SUT directory:
#
#   docker build -f suts/sut-torch-cpu-base.Dockerfile \
#     -t retention-bench/sut-torch-cpu-base:0.1 suts/
#   docker build -t retention-bench/sut-constructive:0.1 suts/constructive/
#
# At runtime the harness runs `docker run -w /dir … <image> python -m constructive`
# (entrypoint from sut-manifest.json); DIR is bind-mounted at /dir and
# RETENTION_BENCH_DIR=/dir is set, so the checkpoint lands in DIR and survives
# RESET. The model is from-scratch and offline — no HF downloads, no network.
FROM retention-bench/sut-torch-cpu-base:0.1

WORKDIR /opt/sut

# --no-deps: torch (the only declared dependency) is already provided by the
# CPU base. Installing without deps avoids pip trying to re-resolve torch from
# the default PyPI index (which would pull the CUDA build). The expensive torch
# layer lives in the base and caches independently of source edits here.
COPY pyproject.toml ./
COPY constructive/ constructive/
RUN pip install --no-deps .

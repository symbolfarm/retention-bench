# Separate CPU-only torch base for the constructive (train-and-grow) SUT.
#
# Deliberately NOT folded into sut-python-base (decided 2026-05-30, task B4b):
# torch is ~1GB and only the constructive SUT needs it, so keeping it in its
# own base leaves the API trio's shared base slim.
#
#   docker build -f suts/sut-torch-cpu-base.Dockerfile \
#     -t retention-bench/sut-torch-cpu-base:0.1 suts/
#
# Pins CPU-only torch via the PyTorch CPU wheel index, matching the pin in
# suts/constructive/pyproject.toml (torch>=2.1,<3). The CPU index serves wheels
# with no CUDA payload, so the image stays CPU-only and offline at runtime.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# CPU-only torch from the dedicated PyTorch CPU index. Selecting the wheel via
# --index-url is what keeps the CUDA payload out (the default PyPI torch wheel
# bundles CUDA libs). Pin range mirrors constructive/pyproject.toml.
RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.1,<3"

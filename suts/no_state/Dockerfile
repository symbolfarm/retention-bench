# no_state reference SUT image.
#
# Extends the shared API base (anthropic SDK pre-installed). Build the base
# first, then this image from the SUT directory:
#
#   docker build -f suts/sut-python-base.Dockerfile \
#     -t retention-bench/sut-python-base:0.1 suts/
#   docker build -t retention-bench/sut-no-state:0.1 suts/no_state/
#
# At runtime the harness runs `docker run -w /dir … <image> python -m no_state`
# (entrypoint from sut-manifest.json); DIR is bind-mounted at /dir. The package
# is installed into the image below so `python -m no_state` resolves regardless
# of the /dir workdir.
FROM retention-bench/sut-python-base:0.1

WORKDIR /opt/sut

# Source (and pyproject) copied together, then installed. anthropic — the only
# dependency — already lives in the base layer, so --no-deps keeps this layer
# cheap and avoids re-resolving it. The expensive dependency layer is in the
# shared base and caches across all three API SUTs.
COPY pyproject.toml ./
COPY no_state/ no_state/
RUN pip install --no-deps .

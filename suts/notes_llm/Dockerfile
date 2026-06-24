# notes_llm reference SUT image.
#
# Extends the shared API base (openai SDK pre-installed). Build the base
# first, then this image from the SUT directory:
#
#   docker build -f suts/sut-python-base.Dockerfile \
#     -t retention-bench/sut-python-base:0.1 suts/
#   docker build -t retention-bench/sut-notes-llm:0.1 suts/notes_llm/
#
# At runtime the harness runs `docker run -w /dir … <image> python -m notes_llm`
# (entrypoint from sut-manifest.json); DIR is bind-mounted at /dir. The package
# is installed into the image below so `python -m notes_llm` resolves regardless
# of the /dir workdir.
FROM retention-bench/sut-python-base:0.1

WORKDIR /opt/sut

# --no-deps: openai (the only dependency) is already provided by the base
# layer, shared across all three API SUTs.
COPY pyproject.toml ./
COPY notes_llm/ notes_llm/
RUN pip install --no-deps .

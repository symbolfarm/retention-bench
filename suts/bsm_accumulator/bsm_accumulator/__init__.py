"""Keyless accumulator reference SUT for retention-bench.

The offline, dependency-light system under test that backs the canonical smoke
(`./run.sh smoke`). It speaks `retention_bench.SubprocessSystem`'s one-line-JSON
contract and drives Continual Learning Bench's ``blind_spectrum_monitoring``
task with no API key and no model weights.

Strategy: each scan reveals only the *currently active* transmitters' peaks; the
task scores against *all persistent* transmitters (including ones dormant on the
current scan). So the SUT **unions the peaks it has seen into the survive-dir**
and reports the full accumulated set every scan. State carried across hard resets
(it lives in the survive-dir) recovers dormant transmitters; a wiped/stateless
arm only ever reports the current scan's subset. That gap *is* the retention
signal — ceiling (state accumulates) scores above the stateless prior.

This is a plumbing/illustration SUT, not a sophisticated detector: it cannot tell
genuine channel peaks from interference (the rendered prompt drops the peak
``source``), and it does no signal processing. That is deliberate — it needs to
be just smart enough to make the retention band legible.
"""

__version__ = "0.1.0"

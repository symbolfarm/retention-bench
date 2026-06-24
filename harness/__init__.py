"""retention-bench harness package.

Reduced by C20 to the two SUT-process primitives the CL-Bench extension reuses:
``sut_process`` (subprocess / container launch, the JSONL wire contract, and
hard-reset teardown) and ``dir_lifecycle`` (survive-dir accounting + snapshots).
``retention_bench.SubprocessSystem`` is built on both. The book-track event-loop
driver, task loader, and trace writer were retired with the book-track; see
``.tasks/debriefs/C20-*``.
"""

__version__ = "0.1.0"

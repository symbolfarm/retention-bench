"""retention-bench harness package.

Reduced to the two SUT-process primitives the CL-Bench extension reuses:
``sut_process`` (subprocess / container launch, the JSONL wire contract, and
hard-reset teardown) and ``dir_lifecycle`` (survive-dir accounting + snapshots).
``retention_bench.SubprocessSystem`` is built on both. The pre-pivot
book-track event-loop driver, task loader, and trace writer were retired when
the project became a CL-Bench extension.
"""

__version__ = "0.1.0"

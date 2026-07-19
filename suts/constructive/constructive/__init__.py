"""Constructive (train-and-grow) reference SUT for retention-bench.

A worked example of the train-and/or-grow integration seam. On each
READ it takes a bounded gradient step on the READ text (self-supervised
next-token LM loss) and periodically grows capacity; it flushes a checkpoint to
DIR that survives RESET; and it answers QUIZ by generating from current weights.

Model quality is an explicit NON-GOAL. This demonstrates that a weights-mutating
SUT integrates with the harness's process + DIR contract; the real constructive
transformer is developed elsewhere.
"""

__version__ = "0.1.0"

"""Reset schedules: when does the SubprocessSystem hard-bounce its SUT?

CL-Bench's runner exposes a single boolean, ``reset_between_instances`` — it
either resets the system after *every* completed instance (k=1 reset density)
or never. A retention *curve* over reset density ``k`` needs per-boundary
control. The adapter design owns this **system-side**: run the
runner with ``reset_between_instances=False`` and let the system decide, from
inside ``observe()``, whether to bounce after each completed instance.

A ``ResetSchedule`` answers one question: given that the run has just completed
its ``n``-th instance (1-based), should the system hard-reset now? The
``SubprocessSystem`` consults it on every instance-complete boundary.

Boundaries are keyed by the **1-based count of completed instances in the run**
(not by ``Query.instance_index``). That ordinal is always dense and monotonic,
whereas ``instance_index`` is a canonical id that a shuffled/subset run may
deliver out of order — keying density off it would make "reset every 3rd
instance" mean different things across runs. The drift experiments place
resets on/off concept-drift boundaries; since drift is injected at fixed run
positions, the run ordinal is the right axis for that too.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol, runtime_checkable


@runtime_checkable
class ResetSchedule(Protocol):
    """Decides whether to hard-reset after the n-th completed instance."""

    def should_reset(self, completed_instances: int) -> bool:
        """``completed_instances`` is 1-based: 1 after the first instance, etc."""
        ...

    @property
    def label(self) -> str:
        """Short identifier recorded in usage-event metadata / traces."""
        ...


@dataclass(frozen=True)
class NoReset:
    """Never bounce — the stateful ceiling (k=0). State accumulates unbroken."""

    def should_reset(self, completed_instances: int) -> bool:  # noqa: ARG002
        return False

    @property
    def label(self) -> str:
        return "no_reset"


@dataclass(frozen=True)
class EveryNInstances:
    """Bounce after every ``n``-th completed instance (reset density k=1/n).

    ``n=1`` reproduces the runner's ``reset_between_instances=True`` density but
    system-side, so it composes with the same accounting path as every other
    density. The final boundary is *not* special-cased here — the
    ``SubprocessSystem`` skips a bounce when there is no next query, so a reset
    that the schedule places on the last instance is simply never acted on.
    """

    n: int

    def __post_init__(self) -> None:
        if self.n < 1:
            raise ValueError(f"EveryNInstances.n must be >= 1, got {self.n}")

    def should_reset(self, completed_instances: int) -> bool:
        return completed_instances % self.n == 0

    @property
    def label(self) -> str:
        return f"every_{self.n}"


@dataclass(frozen=True)
class ExplicitBoundaries:
    """Bounce after exactly the listed (1-based) completed-instance ordinals.

    Lets an experiment place resets deliberately — e.g. on or just off a concept-drift
    boundary — to expose the non-monotonic retention story (a reset that lands
    on drift can *help* by clearing stale belief). Ordinals outside the run
    length are harmless: they simply never fire.
    """

    boundaries: frozenset[int]

    def __init__(self, boundaries: Iterable[int]) -> None:
        bset = frozenset(int(b) for b in boundaries)
        bad = [b for b in bset if b < 1]
        if bad:
            raise ValueError(
                f"ExplicitBoundaries ordinals are 1-based and must be >= 1; got {sorted(bad)}"
            )
        object.__setattr__(self, "boundaries", bset)

    def should_reset(self, completed_instances: int) -> bool:
        return completed_instances in self.boundaries

    @property
    def label(self) -> str:
        return "boundaries:" + ",".join(str(b) for b in sorted(self.boundaries))

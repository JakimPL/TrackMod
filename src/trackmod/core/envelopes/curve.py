from collections.abc import Sequence
from typing import Final

from pydantic import BaseModel, Field

from trackmod.core.envelopes.envelope import Envelope
from trackmod.core.envelopes.point import EnvelopePoint
from trackmod.core.envelopes.span import EnvelopeSpan
from trackmod.core.timing.clock import elapsed_ticks, tick_seconds
from trackmod.limits.bound import Bound
from trackmod.schema.config import FROZEN

TICK_APART: Final = 1


class Breakpoint(BaseModel):
    """One point of a curve stated in time: the value it reaches ``seconds`` after a voice starts."""

    model_config = FROZEN

    seconds: float = Field(ge=0.0)
    value: int


def placed_ticks(breakpoints: Sequence[Breakpoint], *, tempo: int, bound: Bound) -> tuple[int, ...]:
    """Where each breakpoint lands on the tick grid, ascending and inside ``bound``.

    A format reads its breakpoints in order and separates them by at least a tick, so two that round onto
    the same tick are moved apart, and a curve reaching past the last tick a format counts is drawn back
    into the ticks that remain. Each breakpoint keeps room for the ones behind it, which is what keeps
    the end of a curve stated where a format would otherwise be handed points it cannot order.

    Raises:
        ValueError: when the breakpoints outnumber the ticks in ``bound``, leaving nowhere to separate them.
    """
    if len(breakpoints) > bound.room:
        raise ValueError(f"{len(breakpoints)} breakpoints ask for more than the {bound.room} ticks in {bound}")

    placed: list[int] = []
    for index, point in enumerate(breakpoints):
        lowest = placed[-1] + TICK_APART if placed else bound.minimum
        highest = bound.maximum - (len(breakpoints) - 1 - index)
        placed.append(min(max(elapsed_ticks(point.seconds, tempo), lowest), highest))

    return tuple(placed)


def timed_envelope(
    breakpoints: Sequence[Breakpoint],
    *,
    tempo: int,
    tick_bound: Bound,
    value_bound: Bound,
    loop: EnvelopeSpan | None = None,
    sustain: EnvelopeSpan | None = None,
) -> Envelope:
    """An envelope holding a curve given in time, written onto the tick grid ``tempo`` runs.

    A caller fitting a curve to a recording works in seconds and levels; a format stores ticks and node
    values inside its own ranges. This states the curve once in the terms it was measured in and hands a
    format what it holds: each breakpoint at the tick it falls on, each value on the grid ``value_bound``
    names, both spans over the breakpoint indices as given.

    Ticks are relative to ``tempo``, so the same curve written for a different clock is a different
    envelope -- which is why the tempo a curve was fitted at is worth keeping beside it.

    Raises:
        ValueError: when the breakpoints outnumber the ticks in ``tick_bound``, or when a span reaches
            past the breakpoints given.
    """
    ticks = placed_ticks(breakpoints, tempo=tempo, bound=tick_bound)
    points = tuple(
        EnvelopePoint(tick=tick, value=value_bound.clamp(point.value)) for tick, point in zip(ticks, breakpoints)
    )
    return Envelope(points=points, loop=loop, sustain=sustain)


def envelope_seconds(envelope: Envelope, *, tempo: int) -> tuple[Breakpoint, ...]:
    """The curve an envelope holds, read back in time at the tempo it was written for.

    This is the way back from :func:`timed_envelope`, for a caller measuring what a stored curve does
    against the trajectory it was fitted to.
    """
    length = tick_seconds(tempo)
    return tuple(Breakpoint(seconds=point.tick * length, value=point.value) for point in envelope.points)

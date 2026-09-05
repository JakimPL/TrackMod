from collections.abc import Sequence

from trackmod.core.envelopes.point import EnvelopePoint
from trackmod.core.envelopes.span import EnvelopeSpan
from trackmod.core.repairs.report import Repairs
from trackmod.limits.bound import Bound


def repaired_span(
    bounds: tuple[int, int] | None,
    *,
    points: int,
    name: str,
    subject: str,
    repairs: Repairs,
) -> EnvelopeSpan | None:
    """The pair of point indices a file states, drawn inside the points the envelope holds.

    A tracker states a loop or a sustain as a pair of point indices, and files carry pairs reaching past
    the last point or ending before they begin. Both are drawn back to the points that exist: the end to
    the last point, then the begin to the end, which is the reading players settled on. The pair is taken
    as the two numbers the record holds, since a span ending before it begins is one this model states no
    span for.
    """
    if bounds is None:
        return None

    stated_begin, stated_end = bounds
    end = min(stated_end, points - 1)
    begin = min(stated_begin, end)
    if (begin, end) != (stated_begin, stated_end):
        repairs.made(f"{name} span {stated_begin}..{stated_end} drawn to {begin}..{end}", subject=subject)

    return EnvelopeSpan(begin=begin, end=end)


def repaired_points(
    points: Sequence[EnvelopePoint],
    *,
    subject: str,
    repairs: Repairs,
) -> tuple[EnvelopePoint, ...]:
    """Stored breakpoints put in tick order, holding each one at the tick the one before it reached.

    A curve is read in the order its points are stored, so a point stated at an earlier tick than the
    one before it is played the moment that one is. Files carry such points where a tracker left the
    node table longer than the count it uses.
    """
    ordered: list[EnvelopePoint] = []
    for point in points:
        reached = ordered[-1].tick if ordered else point.tick
        ordered.append(point if point.tick >= reached else EnvelopePoint(tick=reached, value=point.value))

    moved = sum(1 for before, after in zip(points, ordered) if before.tick != after.tick)
    if moved:
        repairs.made(f"{moved} envelope points stated out of order held at the tick before them", subject=subject)

    return tuple(ordered)


def levelled_points(
    points: Sequence[EnvelopePoint],
    *,
    bound: Bound,
    subject: str,
    repairs: Repairs,
) -> tuple[EnvelopePoint, ...]:
    """Stored breakpoints drawn inside the levels a format's own field holds.

    A tracker states each breakpoint's level in the width its record keeps and leaves the nodes past the
    count it uses as it found them, so a file states levels in nodes no curve reaches. Each is drawn to
    the nearest level the field holds, which keeps the curve the file meant.
    """
    drawn = tuple(EnvelopePoint(tick=point.tick, value=bound.clamp(point.value)) for point in points)
    moved = sum(1 for before, after in zip(points, drawn) if before.value != after.value)
    if moved:
        repairs.made(f"{moved} envelope levels drawn inside {bound}", subject=subject)

    return drawn

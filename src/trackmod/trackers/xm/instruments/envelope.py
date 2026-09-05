from trackmod.binary.records.values import (
    ArrayValue,
    FieldValue,
    RecordValues,
    read_int,
    read_rows,
)
from trackmod.core.envelopes.envelope import Envelope
from trackmod.core.envelopes.kind import EnvelopeKind
from trackmod.core.envelopes.point import EnvelopePoint
from trackmod.core.envelopes.repair import levelled_points, repaired_points, repaired_span
from trackmod.core.envelopes.span import EnvelopeSpan
from trackmod.core.repairs.report import Repairs
from trackmod.trackers.xm.layout.envelope import envelope_field
from trackmod.trackers.xm.spec.flags import EnvelopeFlag
from trackmod.trackers.xm.spec.ranges import ENVELOPE_LEVELS
from trackmod.trackers.xm.spec.sizes import ENVELOPE_POINTS

EnvelopeValues = dict[str, FieldValue | ArrayValue]


def sustain_point(span: EnvelopeSpan) -> int:
    """The single point this format holds an envelope on while a note is held.

    Raises:
        ValueError: when the span covers more than one point, which this format has no room for.
    """
    if span.begin != span.end:
        raise ValueError(f"this format sustains on one point, got the span {span.begin}..{span.end}")

    return span.begin


def envelope_values(kind: EnvelopeKind, envelope: Envelope | None) -> EnvelopeValues:
    """The record fields one envelope holds, padded out to the point table's fixed length."""
    flags = EnvelopeFlag(0)
    points: list[tuple[int, int]] = []
    sustain, loop_begin, loop_end = 0, 0, 0
    if envelope is not None:
        flags |= EnvelopeFlag.ENABLED
        if envelope.sustain is not None:
            flags |= EnvelopeFlag.SUSTAIN
            sustain = sustain_point(envelope.sustain)

        if envelope.loop is not None:
            flags |= EnvelopeFlag.LOOP
            loop_begin, loop_end = envelope.loop.begin, envelope.loop.end

        points = [(point.tick, point.value) for point in envelope.points]

    return {
        envelope_field(kind, "count"): len(points),
        envelope_field(kind, "sustain"): sustain,
        envelope_field(kind, "loop_begin"): loop_begin,
        envelope_field(kind, "loop_end"): loop_end,
        envelope_field(kind, "flags"): int(flags),
        envelope_field(kind, "points"): tuple(points) + ((0, 0),) * (ENVELOPE_POINTS - len(points)),
    }


def parse_envelope(
    kind: EnvelopeKind,
    values: RecordValues,
    *,
    subject: str,
    repairs: Repairs,
) -> Envelope | None:
    """Rebuild one envelope from its header fields, or ``None`` when it is switched off.

    A level past what the record's own field holds, a loop the header states past the points it counts
    or ending before it begins, and a sustain point past the last one, are drawn back onto what the
    envelope holds and recorded in ``repairs``.
    """
    flags = EnvelopeFlag(read_int(values, envelope_field(kind, "flags")))
    count = read_int(values, envelope_field(kind, "count"))
    if EnvelopeFlag.ENABLED not in flags or count == 0:
        return None

    stated = read_rows(values, envelope_field(kind, "points"))[:count]
    held = read_int(values, envelope_field(kind, "sustain"))
    loop = (
        (read_int(values, envelope_field(kind, "loop_begin")), read_int(values, envelope_field(kind, "loop_end")))
        if EnvelopeFlag.LOOP in flags
        else None
    )
    sustain = (held, held) if EnvelopeFlag.SUSTAIN in flags else None
    levelled = levelled_points(
        [EnvelopePoint(tick=tick, value=value) for tick, value in stated],
        bound=ENVELOPE_LEVELS,
        subject=subject,
        repairs=repairs,
    )
    points = repaired_points(levelled, subject=subject, repairs=repairs)
    held = len(points)
    return Envelope(
        points=points,
        loop=repaired_span(loop, points=held, name=f"{kind} loop", subject=subject, repairs=repairs),
        sustain=repaired_span(sustain, points=held, name=f"{kind} sustain", subject=subject, repairs=repairs),
    )

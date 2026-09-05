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
from trackmod.core.envelopes.repair import repaired_points, repaired_span
from trackmod.core.envelopes.span import EnvelopeSpan
from trackmod.core.repairs.report import Repairs
from trackmod.trackers.it.layout.envelope import envelope_field
from trackmod.trackers.it.spec.flags import EnvelopeFlag
from trackmod.trackers.it.spec.sizes import ENVELOPE_NODES

EnvelopeValues = dict[str, FieldValue | ArrayValue]


def span_bounds(span: EnvelopeSpan | None) -> tuple[int, int]:
    """The pair of point indices a span stores, which is empty when the envelope carries no span."""
    return (0, 0) if span is None else (span.begin, span.end)


def envelope_values(kind: EnvelopeKind, envelope: Envelope | None) -> EnvelopeValues:
    """The record fields one envelope block holds, padded out to the node table's fixed length."""
    flags = EnvelopeFlag(0)
    nodes: list[tuple[int, int]] = []
    loop_begin, loop_end = 0, 0
    sustain_begin, sustain_end = 0, 0
    if envelope is not None:
        flags |= EnvelopeFlag.ENABLED
        if envelope.loop is not None:
            flags |= EnvelopeFlag.LOOP

        if envelope.sustain is not None:
            flags |= EnvelopeFlag.SUSTAIN

        loop_begin, loop_end = span_bounds(envelope.loop)
        sustain_begin, sustain_end = span_bounds(envelope.sustain)
        nodes = [(point.value, point.tick) for point in envelope.points]

    return {
        envelope_field(kind, "flags"): int(flags),
        envelope_field(kind, "count"): len(nodes),
        envelope_field(kind, "loop_begin"): loop_begin,
        envelope_field(kind, "loop_end"): loop_end,
        envelope_field(kind, "sustain_begin"): sustain_begin,
        envelope_field(kind, "sustain_end"): sustain_end,
        envelope_field(kind, "nodes"): tuple(nodes) + ((0, 0),) * (ENVELOPE_NODES - len(nodes)),
    }


def stored_span(kind: EnvelopeKind, values: RecordValues, *, name: str) -> tuple[int, int]:
    """The pair of point indices one of an envelope block's two spans states."""
    return (
        read_int(values, envelope_field(kind, f"{name}_begin")),
        read_int(values, envelope_field(kind, f"{name}_end")),
    )


def parse_envelope(
    kind: EnvelopeKind,
    values: RecordValues,
    *,
    subject: str,
    repairs: Repairs,
) -> Envelope | None:
    """Rebuild one envelope from its block of header fields, or ``None`` when the block is switched off.

    A span the block states past the nodes it counts, or ending before it begins, is drawn back onto the
    nodes that are there and recorded in ``repairs``.
    """
    flags = EnvelopeFlag(read_int(values, envelope_field(kind, "flags")))
    count = read_int(values, envelope_field(kind, "count"))
    if EnvelopeFlag.ENABLED not in flags or count == 0:
        return None

    nodes = read_rows(values, envelope_field(kind, "nodes"))[:count]
    points = repaired_points(
        [EnvelopePoint(tick=tick, value=value) for value, tick in nodes], subject=subject, repairs=repairs
    )
    spans: dict[str, tuple[int, int] | None] = {
        name: stored_span(kind, values, name=name) if flag in flags else None
        for name, flag in (("loop", EnvelopeFlag.LOOP), ("sustain", EnvelopeFlag.SUSTAIN))
    }
    return Envelope(
        points=points,
        loop=repaired_span(spans["loop"], points=len(points), name=f"{kind} loop", subject=subject, repairs=repairs),
        sustain=repaired_span(
            spans["sustain"], points=len(points), name=f"{kind} sustain", subject=subject, repairs=repairs
        ),
    )

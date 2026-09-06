from collections.abc import Sequence
from typing import Final

from trackmod.binary.cursor import Cursor
from trackmod.binary.records.values import RecordValues, read_bytes, read_int
from trackmod.core.patterns.grid import Pattern
from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.spec.grid import EMPTY
from trackmod.trackers.amiga.layout.sample import SAMPLE_HEADER
from trackmod.trackers.amiga.patterns.parser import unpack_pattern
from trackmod.trackers.amiga.samples.parser import parse_sample, stated_frames, stored_bytes
from trackmod.trackers.amiga.spec.ranges import MAX_ORDERS, PATTERN_ROWS
from trackmod.trackers.amiga.spec.sizes import SAMPLE_TABLE_OFFSET

NO_PATTERNS: Final = 0


def read_records(data: bytes, *, slots: int) -> tuple[RecordValues, ...]:
    """Every sample record the header carries, read from the table that opens after the module name."""
    table = Cursor(data)
    table.seek(SAMPLE_TABLE_OFFSET)
    return tuple(table.read(SAMPLE_HEADER) for _ in range(slots))


def read_order(sequence: RecordValues, *, repairs: Repairs) -> tuple[int, ...]:
    """The positions a song plays, drawn back inside the table they sit in.

    The header states how far the order runs in one byte, and the table it names holds 128 positions,
    so a count past that reads as the table and says so.
    """
    stated = read_int(sequence, "order_count")
    count = min(stated, MAX_ORDERS)
    if count != stated:
        repairs.made(f"an order of {stated} positions read as the {MAX_ORDERS} the table holds", subject="song")

    return tuple(read_bytes(sequence, "orders")[:count])


def pattern_count(
    data: bytes,
    *,
    order: OrderList,
    records: Sequence[RecordValues],
    header_bytes: int,
    pattern_bytes: int,
    maximum: int,
    repairs: Repairs,
) -> int:
    """How many patterns a file holds, which it states in two ways that can disagree.

    The order table names the highest one a song plays, and the length left between the header and the
    waveforms holds however many were stored — a module carrying patterns its order never reaches has
    more than it names. Taking the larger keeps both, and reading the waveforms at the right offset
    depends on it.

    The room left between the header and the waveforms is what bounds the pair, because a table naming
    more patterns than the file holds would otherwise read the waveforms as music. The last pattern the
    room reaches counts even where the file stops inside it, so a file cut short still gives up the
    music it holds.
    """
    named = max((entry + 1 for entry in order.entries), default=NO_PATTERNS)
    waveforms = sum(stored_bytes(values) for values in records)
    room = max(len(data) - header_bytes - waveforms, 0)
    counted = min(max(named, room // pattern_bytes), maximum)
    reached = -(-room // pattern_bytes)
    if counted <= reached:
        return counted

    repairs.made(f"an order naming {counted} patterns read as the {reached} the file holds", subject="song")
    return reached


def read_patterns(cursor: Cursor, *, count: int, channels: int, repairs: Repairs) -> tuple[Pattern, ...]:
    """Every pattern the file holds, each a fixed grid of cells and no header of its own."""
    return tuple(
        unpack_pattern(
            cursor,
            rows=PATTERN_ROWS,
            channels=channels,
            subject=f"pattern {index}",
            repairs=repairs,
        )
        for index in range(count)
    )


def read_samples(
    cursor: Cursor,
    records: Sequence[RecordValues],
    *,
    begin_unit: int,
    repairs: Repairs,
) -> tuple[Sample, ...]:
    """Every waveform the file holds, taken in the order its record was written."""
    return tuple(
        parse_sample(
            values,
            stated_frames(cursor, values, subject=f"sample {slot}", repairs=repairs),
            begin_unit=begin_unit,
            subject=f"sample {slot}",
            repairs=repairs,
        )
        for slot, values in enumerate(records)
    )


def held_samples(samples: Sequence[Sample], patterns: Sequence[Pattern]) -> tuple[Sample, ...]:
    """The slots a song keeps: every one up to the last the file states something about.

    A file writes all its records whatever it fills. A slot states something where it holds a waveform,
    where a cell names it, or where it carries a name — the trackers of this lineage wrote text into the
    sample names, so a named slot holding nothing is still text the file carries. The trailing slots
    past all of that state nothing and are left out, while the empty slots before them stay, because the
    cells number their samples by position.
    """
    sounded = max((slot + 1 for slot, sample in enumerate(samples) if sample.frames), default=0)
    named = max((slot + 1 for slot, sample in enumerate(samples) if sample.name), default=0)
    highest = max((int(pattern.instrument.max()) for pattern in patterns if pattern.instrument.size), default=EMPTY)
    return tuple(samples[: max(sounded, named, highest + 1)])

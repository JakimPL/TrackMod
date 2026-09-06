from typing import Final

from trackmod.binary.cursor import Cursor
from trackmod.binary.records.values import RecordValues, read_int
from trackmod.binary.warnings import UnnamedBytes
from trackmod.core.effects.effect import Effect
from trackmod.core.notes.command import NoteValue
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.column import Column
from trackmod.core.patterns.grid import Pattern
from trackmod.core.repairs.report import Repairs
from trackmod.core.volumes.command import VolumeValue
from trackmod.spec.grid import EMPTY
from trackmod.trackers.xm.layout.pattern import PATTERN_HEADER
from trackmod.trackers.xm.note import decode_note
from trackmod.trackers.xm.spec.cells import (
    INSTRUMENT_OFFSET,
    NO_EFFECT,
    NO_INSTRUMENT,
    RAW_CELL_COLUMNS,
    VOLUME_COLUMN_EMPTY,
    CellMask,
)
from trackmod.trackers.xm.spec.ranges import DEFAULT_ROWS, MIN_ROWS
from trackmod.trackers.xm.spec.volume import VOLUME_COLUMN

COLUMN_BITS: Final = (
    CellMask.NOTE,
    CellMask.INSTRUMENT,
    CellMask.VOLUME,
    CellMask.EFFECT,
    CellMask.PARAMETER,
)


def payload_bytes(first: int) -> int:
    """How many bytes a cell states beyond the byte that opens it.

    A first byte with the high bit clear is itself the note and the other four columns follow it whole;
    otherwise the byte is a mask, and each column it names costs one byte.
    """
    if not first & CellMask.PACKED:
        return RAW_CELL_COLUMNS - 1

    return sum(1 for bit in COLUMN_BITS if first & bit)


def stated_columns(first: int, cursor: Cursor) -> list[int]:
    """The five column values one stored cell carries, absent where it states nothing.

    A first byte with the high bit clear is itself the note and the other four columns follow it whole;
    otherwise the byte is a mask and only the columns it names are present.
    """
    if not first & CellMask.PACKED:
        return [first, *cursor.take(RAW_CELL_COLUMNS - 1)]

    return [cursor.byte() if first & bit else EMPTY for bit in COLUMN_BITS]


def stated_note(byte: int, unnamed: UnnamedBytes) -> NoteValue | None:
    """The note a stored byte states, recording a byte this format's note column leaves unnamed."""
    note = decode_note(byte)
    if note is None:
        unnamed.met(byte, column=Column.NOTE)

    return note


def stated_volume(byte: int, unnamed: UnnamedBytes) -> VolumeValue | None:
    """The volume a stored byte states, recording a byte this format's column leaves unnamed.

    The byte a cell writes where it states no volume names an absence rather than an unknown, so it is
    read as one and passes without report.
    """
    volume = VOLUME_COLUMN.stated(byte)
    if volume is None and byte != VOLUME_COLUMN_EMPTY:
        unnamed.met(byte, column=Column.VOLUME)

    return volume


def decode_effect(command: int, parameter: int) -> Effect | None:
    """The effect a cell's two columns state, reading an empty pair of them as a cell with no effect."""
    stated, argument = max(command, NO_EFFECT), max(parameter, NO_EFFECT)
    if stated == NO_EFFECT and argument == NO_EFFECT:
        return None

    return Effect(command=stated, parameter=argument)


def decode_cell(first: int, cursor: Cursor, unnamed: UnnamedBytes) -> Cell:
    """One cell, read from the byte that opens it and the columns that byte names."""
    note, instrument, volume, command, parameter = stated_columns(first, cursor)
    return Cell(
        note=None if note == EMPTY else stated_note(note, unnamed),
        instrument=None if instrument in (EMPTY, NO_INSTRUMENT) else instrument - INSTRUMENT_OFFSET,
        volume=None if volume == EMPTY else stated_volume(volume, unnamed),
        effect=decode_effect(command, parameter),
    )


def unpack_cells(stream: bytes, *, rows: int, channels: int, subject: str, repairs: Repairs) -> Pattern:
    """Rebuild a pattern grid from a stored cell stream of a known size.

    A stream ending before the grid does leaves the rest of the grid silent, which is what a player
    sounds where the cells run out.
    """
    if not stream:
        return Pattern.empty(rows=rows, channels=channels)

    cursor = Cursor(stream)
    unnamed = UnnamedBytes()
    builder = PatternBuilder(rows=rows, channels=channels)
    cells = rows * channels
    placed = 0
    while placed < cells and not cursor.at_end:
        first = cursor.byte()
        if cursor.remaining < payload_bytes(first):
            repairs.made("a cell the stream stops inside reads as silence", subject=subject)
            break

        builder.place(placed // channels, placed % channels, decode_cell(first, cursor, unnamed))
        placed += 1

    if placed < cells:
        repairs.made(f"{cells - placed} cells past the end of the stream read as silence", subject=subject)

    unnamed.warn()
    return builder.build()


def stated_rows(header: RecordValues, *, subject: str, repairs: Repairs) -> int:
    """How tall a pattern's header states it is, at the height a tracker plays where it states none."""
    rows = read_int(header, "rows")
    if rows >= MIN_ROWS:
        return rows

    repairs.made(f"a header stating {rows} rows reads as {DEFAULT_ROWS}", subject=subject)
    return DEFAULT_ROWS


def unpack_pattern(cursor: Cursor, *, channels: int, subject: str, repairs: Repairs) -> Pattern:
    """Read one pattern — its header and its cell stream — from the cursor's position.

    A file stopping inside the header states it as far as it holds it, which reads the pattern's rows as
    far as they go.
    """
    header = PATTERN_HEADER.unpack(cursor.peek_padded(PATTERN_HEADER.size))
    cursor.take_at_most(PATTERN_HEADER.size)
    rows = stated_rows(header, subject=subject, repairs=repairs)
    stream = cursor.take_at_most(read_int(header, "packed_size"))
    return unpack_cells(stream, rows=rows, channels=channels, subject=subject, repairs=repairs)

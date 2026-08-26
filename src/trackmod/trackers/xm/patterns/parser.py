from typing import Final

from trackmod.binary.cursor import Cursor
from trackmod.binary.records.values import read_int
from trackmod.binary.warnings import UnnamedBytes
from trackmod.core.effects.effect import Effect
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.column import Column
from trackmod.core.patterns.grid import Pattern
from trackmod.core.volumes.command import VolumeValue
from trackmod.spec.grid import EMPTY
from trackmod.spec.levels import MAX_VOLUME
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
from trackmod.trackers.xm.volume import decode_volume

COLUMN_BITS: Final = (
    CellMask.NOTE,
    CellMask.INSTRUMENT,
    CellMask.VOLUME,
    CellMask.EFFECT,
    CellMask.PARAMETER,
)


def stated_columns(cursor: Cursor) -> list[int]:
    """The five column values one stored cell carries, absent where it states nothing.

    A first byte with the high bit clear is itself the note and the other four columns follow it whole;
    otherwise the byte is a mask and only the columns it names are present.
    """
    first = cursor.take(1)[0]
    if not first & CellMask.PACKED:
        return [first, *cursor.take(RAW_CELL_COLUMNS - 1)]

    return [cursor.take(1)[0] if first & bit else EMPTY for bit in COLUMN_BITS]


def stated_volume(byte: int, unnamed: UnnamedBytes) -> VolumeValue | None:
    """The volume a stored byte states, recording a byte this format's column leaves unnamed.

    The byte a cell writes where it states no volume names an absence rather than an unknown, so it is
    read as one and passes without report.
    """
    volume = decode_volume(byte)
    if volume is None and byte != VOLUME_COLUMN_EMPTY:
        unnamed.met(byte, column=Column.VOLUME)

    return volume


def decode_effect(command: int, parameter: int) -> Effect | None:
    """The effect a cell carries, which an empty command with an empty parameter does not."""
    stated, argument = max(command, NO_EFFECT), max(parameter, NO_EFFECT)
    if stated == NO_EFFECT and argument == NO_EFFECT:
        return None

    return Effect(command=stated, parameter=argument)


def decode_cell(cursor: Cursor, unnamed: UnnamedBytes) -> Cell:
    """One cell, read from the cursor's position."""
    note, instrument, volume, command, parameter = stated_columns(cursor)
    return Cell(
        note=None if note == EMPTY else decode_note(note),
        instrument=None if instrument in (EMPTY, NO_INSTRUMENT) else instrument - INSTRUMENT_OFFSET,
        volume=None if volume == EMPTY else stated_volume(volume, unnamed),
        effect=decode_effect(command, parameter),
    )


def unpack_cells(stream: bytes, *, rows: int, channels: int) -> Pattern:
    """Rebuild a pattern grid from a stored cell stream of a known size."""
    if not stream:
        return Pattern.empty(rows=rows, channels=channels)

    cursor = Cursor(stream)
    unnamed = UnnamedBytes()
    builder = PatternBuilder(rows=rows, channels=channels)
    for row in range(rows):
        for channel in range(channels):
            builder.place(row, channel, decode_cell(cursor, unnamed))

    unnamed.warn()
    return builder.build()


def unpack_pattern(cursor: Cursor, *, channels: int) -> Pattern:
    """Read one pattern — its header and its cell stream — from the cursor's position."""
    header = cursor.read(PATTERN_HEADER)
    rows = read_int(header, "rows")
    stream = cursor.take(read_int(header, "packed_size"))
    return unpack_cells(stream, rows=rows, channels=channels)

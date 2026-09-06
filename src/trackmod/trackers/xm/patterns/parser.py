from typing import Final

from trackmod.binary.cursor import Cursor
from trackmod.binary.records.values import read_int
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
from trackmod.trackers.xm.spec.volume import VOLUME_COLUMN

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
    otherwise the byte is a mask and only the columns it names are present. A column the stream ends
    before is read as an absence, which is what a cell cut short by a truncated file holds.
    """
    first = cursor.byte()
    if not first & CellMask.PACKED:
        held = cursor.take_at_most(RAW_CELL_COLUMNS - 1)
        return [first, *held, *([EMPTY] * (RAW_CELL_COLUMNS - 1 - len(held)))]

    return [cursor.byte() if first & bit and not cursor.at_end else EMPTY for bit in COLUMN_BITS]


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


def decode_cell(cursor: Cursor, unnamed: UnnamedBytes) -> Cell:
    """One cell, read from the cursor's position."""
    note, instrument, volume, command, parameter = stated_columns(cursor)
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
        builder.place(placed // channels, placed % channels, decode_cell(cursor, unnamed))
        placed += 1

    if placed < cells:
        repairs.made(f"{cells - placed} cells past the end of the stream read as silence", subject=subject)

    unnamed.warn()
    return builder.build()


def unpack_pattern(cursor: Cursor, *, channels: int, subject: str, repairs: Repairs) -> Pattern:
    """Read one pattern — its header and its cell stream — from the cursor's position."""
    header = cursor.read(PATTERN_HEADER)
    rows = read_int(header, "rows")
    stream = cursor.take_at_most(read_int(header, "packed_size"))
    return unpack_cells(stream, rows=rows, channels=channels, subject=subject, repairs=repairs)

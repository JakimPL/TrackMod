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
from trackmod.spec.grid import EMPTY, MIN_ROWS
from trackmod.trackers.it.layout.pattern import PATTERN_HEADER
from trackmod.trackers.it.note import decode_note
from trackmod.trackers.it.patterns.memory import ChannelMemory
from trackmod.trackers.it.spec.cells import (
    CHANNEL_MARKER,
    COLUMN_BYTES,
    END_OF_ROW,
    INSTRUMENT_OFFSET,
    NO_INSTRUMENT,
    UNSET,
    CellMask,
)
from trackmod.trackers.it.spec.ranges import DEFAULT_ROWS
from trackmod.trackers.it.spec.volume import VOLUME_COLUMN


def decode_column(
    cursor: Cursor,
    mask: int,
    *,
    fresh: CellMask,
    reuse: CellMask,
    remembered: int,
) -> tuple[int, int]:
    """The value this cell carries and the value the channel goes on remembering.

    A column the mask leaves out is absent from the cell and leaves the channel's memory untouched, so a
    later cell can still reuse the value that was last stated.
    """
    if mask & fresh:
        stated = cursor.byte()
        return stated, stated

    if mask & reuse:
        return remembered, remembered

    return EMPTY, remembered


def decode_effect(
    cursor: Cursor,
    mask: int,
    memory: ChannelMemory,
) -> Effect | None:
    """The effect this cell carries, reading the command and parameter bytes only when they are stated."""
    if mask & CellMask.EFFECT:
        memory.command = cursor.byte()
        memory.parameter = cursor.byte()
    elif not mask & CellMask.LAST_EFFECT:
        return None

    if memory.command == UNSET:
        return None

    return Effect(
        command=memory.command,
        parameter=max(memory.parameter, 0),
    )


def stated_note(byte: int, unnamed: UnnamedBytes) -> NoteValue | None:
    """The note a stored byte states, recording a byte this format's note column leaves unnamed."""
    note = decode_note(byte)
    if note is None:
        unnamed.met(byte, column=Column.NOTE)

    return note


def stated_volume(byte: int, unnamed: UnnamedBytes) -> VolumeValue | None:
    """The volume a stored byte states, recording a byte this format's column leaves unnamed."""
    volume = VOLUME_COLUMN.stated(byte)
    if volume is None:
        unnamed.met(byte, column=Column.VOLUME)

    return volume


def decode_cell(cursor: Cursor, memory: ChannelMemory, unnamed: UnnamedBytes) -> Cell:
    """One cell, read against the mask and the values its channel last stated."""
    mask = memory.mask
    note, memory.note = decode_column(
        cursor,
        mask,
        fresh=CellMask.NOTE,
        reuse=CellMask.LAST_NOTE,
        remembered=memory.note,
    )
    instrument, memory.instrument = decode_column(
        cursor,
        mask,
        fresh=CellMask.INSTRUMENT,
        reuse=CellMask.LAST_INSTRUMENT,
        remembered=memory.instrument,
    )
    volume, memory.volume = decode_column(
        cursor,
        mask,
        fresh=CellMask.VOLUME,
        reuse=CellMask.LAST_VOLUME,
        remembered=memory.volume,
    )
    return Cell(
        note=None if note == EMPTY else stated_note(note, unnamed),
        instrument=None if instrument in (EMPTY, NO_INSTRUMENT) else instrument - INSTRUMENT_OFFSET,
        volume=None if volume == EMPTY else stated_volume(volume, unnamed),
        effect=decode_effect(cursor, mask, memory),
    )


def payload_bytes(mask: int) -> int:
    """How many bytes the columns a mask states outright occupy after it."""
    return sum(size for column, size in COLUMN_BYTES.items() if mask & column)


def stated_rows(header: RecordValues, *, subject: str, repairs: Repairs) -> int:
    """How tall a pattern's header states it is, at the height a tracker plays where it states none."""
    rows = read_int(header, "rows")
    if rows >= MIN_ROWS:
        return rows

    repairs.made(f"a block stating {rows} rows reads as {DEFAULT_ROWS}", subject=subject)
    return DEFAULT_ROWS


def unpack_cells(stream: bytes, *, rows: int, subject: str, repairs: Repairs) -> Pattern:
    """Rebuild a pattern grid from a packed cell stream, sized to the widest channel it reaches.

    A row naming a channel without a mask byte carries on with the mask that channel last stated, which
    starts out naming no columns -- so such a cell reads as the silence already sitting there, and the
    channel still counts towards the width.

    A mask says how many bytes its cell spends, so a stream stopping inside one leaves that cell silent
    along with the rows after it, and a marker naming a channel below the first leaves its cell silent
    too. Both are reported.
    """
    cursor = Cursor(stream)
    unnamed = UnnamedBytes()
    memories: dict[int, ChannelMemory] = {}
    placed: list[tuple[int, int, Cell]] = []
    row = 0
    unplaced = 0
    while row < rows and not cursor.at_end:
        marker = cursor.byte()
        if marker == END_OF_ROW:
            row += 1
            continue

        channel = (marker & ~CHANNEL_MARKER) - 1
        memory = memories.setdefault(channel, ChannelMemory())
        if marker & CHANNEL_MARKER and not cursor.at_end:
            memory.mask = cursor.byte()

        if cursor.remaining < payload_bytes(memory.mask):
            repairs.made("a cell the stream stops inside reads as silence", subject=subject)
            break

        cell = decode_cell(cursor, memory, unnamed)
        if channel < 0:
            unplaced += 1
            continue

        placed.append((row, channel, cell))

    if row < rows:
        repairs.made(f"{rows - row} rows past the end of the stream read as silence", subject=subject)

    if unplaced:
        repairs.made(f"{unplaced} cells naming no channel read as silence", subject=subject)

    unnamed.warn()
    channels = max((channel for _, channel, _ in placed), default=0) + 1
    builder = PatternBuilder(rows=rows, channels=channels)
    for row, channel, cell in placed:
        builder.place(row, channel, cell)

    return builder.build()


def unpack_pattern(cursor: Cursor, *, subject: str, repairs: Repairs) -> Pattern:
    """Read one pattern — its header and its cell stream — from the cursor's position.

    A file stopping inside the block states the header and the stream as far as it holds them, which
    reads the pattern's rows as far as they go.
    """
    header = PATTERN_HEADER.unpack(cursor.peek_padded(PATTERN_HEADER.size))
    cursor.take_at_most(PATTERN_HEADER.size)
    stream = cursor.take_at_most(read_int(header, "packed_size"))
    rows = stated_rows(header, subject=subject, repairs=repairs)
    return unpack_cells(stream, rows=rows, subject=subject, repairs=repairs)

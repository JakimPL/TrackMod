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
from trackmod.trackers.s3m.layout.pattern import PATTERN_HEADER
from trackmod.trackers.s3m.note import decode_note
from trackmod.trackers.s3m.spec.cells import (
    CHANNEL_MASK,
    END_OF_ROW,
    GROUP_BYTES,
    NO_EFFECT,
    NO_SAMPLE,
    SAMPLE_OFFSET,
    CellMask,
    NoteByte,
)
from trackmod.trackers.s3m.volume import decode_volume


def stated_note(byte: int, unnamed: UnnamedBytes) -> NoteValue | None:
    """The note a stored byte states, recording a byte this format's note column leaves unnamed."""
    if byte == NoteByte.ABSENT:
        return None

    note = decode_note(byte)
    if note is None:
        unnamed.met(byte, column=Column.NOTE)

    return note


def stated_volume(byte: int, unnamed: UnnamedBytes) -> VolumeValue | None:
    """The volume a stored byte states, recording a byte this format's column leaves unnamed."""
    volume = decode_volume(byte)
    if volume is None:
        unnamed.met(byte, column=Column.VOLUME)

    return volume


def decode_key(cursor: Cursor, unnamed: UnnamedBytes) -> tuple[NoteValue | None, int | None]:
    """The key and the sample the two bytes of a cell's first group carry.

    The pair shares one marker bit, so a cell stating either of them states both bytes and the one it
    leaves alone carries the value that names nothing.
    """
    note, sample = cursor.take(1)[0], cursor.take(1)[0]
    return stated_note(note, unnamed), None if sample == NO_SAMPLE else sample - SAMPLE_OFFSET


def decode_effect(cursor: Cursor) -> Effect | None:
    """The effect a cell carries, which the command a cell writes for none does not."""
    command, parameter = cursor.take(1)[0], cursor.take(1)[0]
    return None if command == NO_EFFECT else Effect(command=command, parameter=parameter)


def payload_bytes(marker: int) -> int:
    """How many bytes the groups a marker names occupy after it."""
    return sum(size for group, size in GROUP_BYTES.items() if marker & group)


def decode_cell(cursor: Cursor, marker: int, unnamed: UnnamedBytes) -> Cell:
    """One cell, read against the groups of bytes its marker says follow."""
    note, sample = decode_key(cursor, unnamed) if marker & CellMask.KEY else (None, None)
    volume = stated_volume(cursor.take(1)[0], unnamed) if marker & CellMask.VOLUME else None
    return Cell(
        note=note,
        instrument=sample,
        volume=volume,
        effect=decode_effect(cursor) if marker & CellMask.EFFECT else None,
    )


def unpack_cells(stream: bytes, *, rows: int, channels: int, subject: str, repairs: Repairs) -> Pattern:
    """Rebuild a pattern grid from a packed cell stream, whose rows are closed one by one.

    A row lists only the channels carrying something and ends with a zero byte, so the stream states its
    own height and a stream ending early leaves the rows it never reached silent. A marker says how many
    bytes its cell spends, so a stream stopping inside one leaves that cell silent along with the rows
    after it.
    """
    cursor = Cursor(stream)
    unnamed = UnnamedBytes()
    builder = PatternBuilder(rows=rows, channels=channels)
    row = 0
    beyond = 0
    while row < rows and not cursor.at_end:
        marker = cursor.take(1)[0]
        if marker == END_OF_ROW:
            row += 1
            continue

        if cursor.remaining < payload_bytes(marker):
            repairs.made("a cell the stream stops inside reads as silence", subject=subject)
            break

        cell = decode_cell(cursor, marker, unnamed)
        channel = marker & CHANNEL_MASK
        if channel < channels:
            builder.place(row, channel, cell)
        else:
            beyond += 1

    if row < rows:
        repairs.made(f"{rows - row} rows past the end of the stream read as silence", subject=subject)

    if beyond:
        repairs.made(f"{beyond} cells on channels past the {channels} stated read as silence", subject=subject)

    unnamed.warn()
    return builder.build()


def unpack_pattern(cursor: Cursor, *, rows: int, channels: int, subject: str, repairs: Repairs) -> Pattern:
    """Read one pattern — the length its block opens with and the cell stream that follows — from a cursor.

    The stated length covers the block a pointer names, the two bytes stating it included in the count
    the trackers of this lineage wrote there, while the row terminators are what delimit the cells. The
    length is therefore read as the room the stream has and the terminators as where it ends, so a block
    counted either way reads to the same music. A block the file stops inside states the length it holds,
    which reads its rows as far as they go.
    """
    header = PATTERN_HEADER.unpack(cursor.peek_padded(PATTERN_HEADER.size))
    cursor.take_at_most(PATTERN_HEADER.size)
    stream = cursor.take_at_most(read_int(header, "block_size"))
    return unpack_cells(stream, rows=rows, channels=channels, subject=subject, repairs=repairs)

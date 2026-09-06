import pytest

from tests.conftest import GridShape, random_pattern
from trackmod.binary.volume import VolumeSpan
from trackmod.binary.warnings import UnnamedByteWarning
from trackmod.core.effects.effect import Effect
from trackmod.core.notes.command import NoteCommand
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.grid import Pattern
from trackmod.core.repairs.report import Repairs
from trackmod.core.volumes.command import VolumeCommand, VolumeEffect
from trackmod.spec.grid import EMPTY, MIN_CHANNELS
from trackmod.trackers.it.patterns.packer import pack_cells, stored_instrument
from trackmod.trackers.it.patterns.parser import stated_rows, unpack_cells
from trackmod.trackers.it.patterns.sizing import packed_bytes
from trackmod.trackers.it.patterns.width import WIDTH_MARKER_BYTES, width_marker
from trackmod.trackers.it.spec.cells import (
    CHANNEL_MARKER,
    NO_COLUMNS,
    NO_INSTRUMENT,
    CellMask,
)
from trackmod.trackers.it.spec.ranges import MAX_ROWS
from trackmod.trackers.it.spec.volume import VOLUME_COLUMN
from trackmod.trackers.it.volume import stored_volume

SUBJECT = "pattern 0"
SILENT_ROWS = 64  # the height this format's own tracker opens a pattern at, and reads a block stating none at

GRIDS = (
    GridShape(rows=16, channels=4, instruments=2, seed=1),
    GridShape(rows=64, channels=12, instruments=3, seed=2),
    GridShape(rows=MAX_ROWS, channels=32, instruments=4, seed=3),
    GridShape(rows=1, channels=1, instruments=1, seed=4),
)


@pytest.mark.parametrize("shape", GRIDS, ids=lambda shape: f"{shape.rows}x{shape.channels}")
def test_the_size_model_agrees_with_the_packer_byte_for_byte(shape: GridShape) -> None:
    pattern = random_pattern(shape)
    assert packed_bytes(pattern) == len(pack_cells(pattern))


def test_a_channel_holding_steady_settles_to_one_byte_a_row() -> None:
    # Row 0 states all three columns, row 1 switches to the all-reuse mask, and from row 2 on the
    # channel byte alone carries the cell: mask, note, instrument and volume all come from memory.
    builder = PatternBuilder(rows=4, channels=1)
    for row in range(4):
        builder.place(row, 0, Cell(note=Note(60), instrument=0, volume=32))

    stream = pack_cells(builder.build())
    stated = 1 + 1 + 3
    switched = 1 + 1
    settled = 1
    assert len(stream) == stated + switched + 2 * settled + 4


def test_a_silent_channel_costs_nothing() -> None:
    # Every row is a lone terminator; the two bytes beyond them are the opening row naming the widest
    # channel, which is what a pattern of pure silence has to spend to come back the width it went in.
    empty = Pattern.empty(rows=8, channels=16)
    assert len(pack_cells(empty)) == empty.rows + WIDTH_MARKER_BYTES


def test_a_pattern_whose_widest_channels_are_silent_keeps_its_width() -> None:
    builder = PatternBuilder(rows=4, channels=12)
    builder.place(0, 0, Cell(note=Note(60), instrument=0, volume=64))
    pattern = builder.build()
    assert unpack_cells(pack_cells(pattern), rows=pattern.rows, subject=SUBJECT, repairs=Repairs()) == pattern


def test_the_widest_channel_states_the_width_by_carrying_content() -> None:
    # A pattern reaching its widest channel with a note needs no cell spent on the width.
    builder = PatternBuilder(rows=4, channels=12)
    builder.place(3, 11, Cell(note=Note(60), instrument=0, volume=64))
    pattern = builder.build()
    assert width_marker(pattern) == b""
    assert unpack_cells(pack_cells(pattern), rows=pattern.rows, subject=SUBJECT, repairs=Repairs()) == pattern


def test_the_width_is_named_by_a_cell_the_grid_reads_as_silence() -> None:
    pattern = Pattern.empty(rows=1, channels=6)
    stream = pack_cells(pattern)
    assert stream[:WIDTH_MARKER_BYTES] == bytes([CHANNEL_MARKER | pattern.channels, NO_COLUMNS])
    assert unpack_cells(stream, rows=1, subject=SUBJECT, repairs=Repairs()).cell(0, pattern.channels - 1) == Cell()


def test_a_changed_volume_spends_a_byte_and_keeps_the_mask() -> None:
    builder = PatternBuilder(rows=2, channels=1)
    builder.place(0, 0, Cell(note=Note(60), instrument=0, volume=32))
    builder.place(1, 0, Cell(note=Note(60), instrument=0, volume=48))
    stream = pack_cells(builder.build())
    # The second row restates only its volume, so its mask differs from the first and is spent again.
    assert stream[-3] == CellMask.LAST_NOTE | CellMask.LAST_INSTRUMENT | CellMask.VOLUME


@pytest.mark.parametrize("shape", GRIDS, ids=lambda shape: f"{shape.rows}x{shape.channels}")
def test_a_packed_pattern_unpacks_to_the_same_grid(shape: GridShape) -> None:
    pattern = random_pattern(shape)
    recovered = unpack_cells(pack_cells(pattern), rows=pattern.rows, subject=SUBJECT, repairs=Repairs()).widened(
        pattern.channels
    )
    assert recovered == pattern


def test_a_note_command_survives_a_round_trip() -> None:
    builder = PatternBuilder(rows=2, channels=1)
    builder.place(0, 0, Cell(note=Note(60), instrument=0, volume=64))
    builder.place(1, 0, Cell(note=NoteCommand.OFF))
    recovered = unpack_cells(pack_cells(builder.build()), rows=2, subject=SUBJECT, repairs=Repairs())
    assert recovered.cell(1, 0) == Cell(note=NoteCommand.OFF)


def test_an_effect_survives_a_round_trip() -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(effect=Effect(command=20, parameter=200)))
    recovered = unpack_cells(pack_cells(builder.build()), rows=1, subject=SUBJECT, repairs=Repairs())
    assert recovered.cell(0, 0) == Cell(effect=Effect(command=20, parameter=200))


def test_a_column_left_out_of_a_cell_does_not_erase_what_the_channel_remembers() -> None:
    # Row 1 states nothing but a note, so row 2 must still be able to reuse row 0's volume.
    builder = PatternBuilder(rows=3, channels=1)
    builder.place(0, 0, Cell(note=Note(60), volume=32))
    builder.place(1, 0, Cell(note=Note(62)))
    builder.place(2, 0, Cell(note=Note(62), volume=32))
    pattern = builder.build()
    recovered = unpack_cells(pack_cells(pattern), rows=3, subject=SUBJECT, repairs=Repairs())
    assert recovered.cell(1, 0) == Cell(note=Note(62))
    assert recovered.cell(2, 0) == Cell(note=Note(62), volume=32)


def test_a_channel_named_before_any_mask_reads_as_silence_and_still_states_the_width() -> None:
    # ITTECH.TXT starts every channel remembering a mask over no columns, and files in the wild name a
    # channel with no mask byte at all. Such a cell carries nothing and still widens the pattern, which
    # is the same reading the width marker relies on.
    recovered = unpack_cells(bytes([0x04, 0x00]), rows=1, subject=SUBJECT, repairs=Repairs())
    assert recovered.channels == 4
    assert recovered.cell(0, 3) == Cell()
    assert not recovered.occupied.any()


def test_the_first_instrument_is_stored_above_the_byte_that_means_none() -> None:
    # Zero is what a cell writes to stay on the instrument the channel already carries, so a stored
    # instrument number starts at one — writing the shared index straight through silences the cell.
    assert stored_instrument(0) == NO_INSTRUMENT + 1
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(note=Note(60), instrument=0, volume=64))
    assert NO_INSTRUMENT not in pack_cells(builder.build())[:-1]


def test_an_instrument_survives_a_round_trip() -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(note=Note(60), instrument=0, volume=64))
    recovered = unpack_cells(pack_cells(builder.build()), rows=1, subject=SUBJECT, repairs=Repairs())
    assert recovered.cell(0, 0).instrument == 0


UNNAMED_EFFECT = VolumeEffect.VIBRATO_SPEED
UNNAMED_BYTE = 213


def volume_stream(byte: int) -> bytes:
    """One packed cell on channel zero stating only a volume, then the end of its row."""
    return bytes([1 | CHANNEL_MARKER, CellMask.VOLUME, byte, 0x00])


def unpack_cells_at(stream: bytes) -> Pattern:
    """The one-row pattern a stream packs to."""
    return unpack_cells(stream, rows=1, subject=SUBJECT, repairs=Repairs())


@pytest.mark.parametrize("span", VOLUME_COLUMN.spans, ids=lambda span: span.effect.name)
def test_every_effect_the_column_names_round_trips_byte_for_byte(span: VolumeSpan) -> None:
    command = VolumeCommand(effect=span.effect, amount=span.amounts.maximum)
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(volume=command))
    stream = pack_cells(builder.build())
    assert span.stored(span.amounts.maximum) in stream
    assert unpack_cells_at(stream).cell(0, 0).volume == command


def test_an_effect_the_column_has_no_run_for_is_refused() -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(volume=VolumeCommand(effect=UNNAMED_EFFECT, amount=0)))
    with pytest.raises(ValueError, match="no run for"):
        pack_cells(builder.build())


def test_an_amount_past_the_run_it_sits_in_is_refused() -> None:
    span = VOLUME_COLUMN.span(VolumeEffect.VOLUME_SLIDE_UP)
    assert span is not None
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(volume=VolumeCommand(effect=span.effect, amount=span.amounts.maximum + 1)))
    with pytest.raises(ValueError, match="lies outside"):
        pack_cells(builder.build())


def test_a_byte_the_column_leaves_unnamed_reads_as_absent_and_is_reported() -> None:
    with pytest.warns(UnnamedByteWarning, match=str(UNNAMED_BYTE)):
        recovered = unpack_cells_at(volume_stream(UNNAMED_BYTE))

    assert recovered.cell(0, 0).volume is None


def test_the_size_model_agrees_with_the_packer_over_volume_commands() -> None:
    builder = PatternBuilder(rows=4, channels=1)
    for row, span in enumerate(VOLUME_COLUMN.spans[:4]):
        builder.place(row, 0, Cell(note=Note(60), volume=VolumeCommand(effect=span.effect, amount=1)))

    pattern = builder.build()
    assert packed_bytes(pattern) == len(pack_cells(pattern))


def test_an_absent_volume_is_written_as_absent() -> None:
    assert stored_volume(EMPTY) == EMPTY


def test_a_note_byte_the_column_leaves_unnamed_reads_as_absent_and_is_reported() -> None:
    # The keys stop at 119 and the commands sit at 253..255, so the values between them name nothing.
    stream = bytes([1 | CHANNEL_MARKER, CellMask.NOTE, 200, 0x00])
    with pytest.warns(UnnamedByteWarning, match="200"):
        recovered = unpack_cells(stream, rows=1, subject=SUBJECT, repairs=Repairs())

    assert recovered.cell(0, 0) == Cell()


def test_the_commands_at_the_top_of_the_byte_range_still_read() -> None:
    stream = bytes([1 | CHANNEL_MARKER, CellMask.NOTE, 255, 0x00])
    assert unpack_cells(stream, rows=1, subject=SUBJECT, repairs=Repairs()).cell(0, 0) == Cell(note=NoteCommand.OFF)


def test_a_stream_stopping_inside_a_cell_reads_it_and_the_rows_after_it_as_silence() -> None:
    # A mask states which columns follow it, so a stream that runs out inside one leaves the cell it
    # opened silent along with every row it never reached.
    stream = bytes([1 | CHANNEL_MARKER, CellMask.NOTE | CellMask.VOLUME, 60])
    repairs = Repairs()

    pattern = unpack_cells(stream, rows=2, subject=SUBJECT, repairs=repairs)

    assert not pattern.occupied.any()
    assert [repair for _, repair in repairs.entries] == [
        "2 rows past the end of the stream read as silence",
        "a cell the stream stops inside reads as silence",
    ]


def test_a_marker_naming_no_channel_reads_as_silence() -> None:
    # The channel byte is one-based, so a marker whose channel bits are all clear names nothing at all.
    repairs = Repairs()

    pattern = unpack_cells(bytes([CHANNEL_MARKER, NO_COLUMNS, 0x00]), rows=1, subject=SUBJECT, repairs=repairs)

    assert pattern.channels == MIN_CHANNELS
    assert not pattern.occupied.any()
    assert [repair for _, repair in repairs.entries] == ["1 cells naming no channel read as silence"]


def test_a_block_stating_no_rows_reads_at_the_height_a_tracker_plays() -> None:
    repairs = Repairs()

    rows = stated_rows({"rows": 0}, subject=SUBJECT, repairs=repairs)

    assert rows == SILENT_ROWS
    assert [repair for _, repair in repairs.entries] == ["a block stating 0 rows reads as 64"]

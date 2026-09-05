import pytest

from tests.trackers.s3m.conftest import ABSENT_NOTE, cell_bytes, pattern_block, s3m_pattern
from trackmod.binary.cursor import Cursor
from trackmod.core.notes.command import NoteCommand
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.grid import Pattern
from trackmod.core.repairs.report import Repairs, RepairWarning
from trackmod.core.volumes.command import VolumeCommand, VolumeEffect
from trackmod.trackers.s3m.patterns.packer import pack_cells, pack_pattern
from trackmod.trackers.s3m.patterns.parser import unpack_cells, unpack_pattern
from trackmod.trackers.s3m.patterns.sizing import block_bytes, packed_bytes
from trackmod.trackers.s3m.spec.ranges import PATTERN_ROWS

CHANNELS = 4
REFERENCE_BYTE = 0x40


def rebuilt(pattern: Pattern, *, channels: int = CHANNELS) -> Pattern:
    repairs = Repairs()
    return unpack_cells(
        pack_cells(pattern),
        rows=pattern.rows,
        channels=channels,
        subject="pattern",
        repairs=repairs,
    )


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_a_grid_survives_being_packed_and_unpacked(seed: int) -> None:
    pattern = s3m_pattern(channels=CHANNELS, samples=3, seed=seed)
    assert rebuilt(pattern) == pattern


def test_silence_costs_one_byte_a_row_and_nothing_else() -> None:
    pattern = Pattern.empty(rows=PATTERN_ROWS, channels=CHANNELS)
    assert packed_bytes(pattern) == PATTERN_ROWS
    assert len(pack_cells(pattern)) == PATTERN_ROWS


@pytest.mark.parametrize("seed", [4, 5, 6])
def test_the_size_model_states_exactly_what_the_packer_writes(seed: int) -> None:
    pattern = s3m_pattern(channels=CHANNELS, samples=3, seed=seed)
    assert packed_bytes(pattern) == len(pack_cells(pattern))
    assert block_bytes(pattern) == len(pack_pattern(pattern))


def test_a_key_and_the_sample_that_sounds_it_are_stated_together() -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(instrument=2))
    stream = pack_cells(builder.build())
    assert stream == cell_bytes(0, note=ABSENT_NOTE, sample=3) + b"\x00"


def test_a_cell_stating_only_a_volume_spends_one_byte_on_it() -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(volume=48))
    assert pack_cells(builder.build()) == cell_bytes(0, volume=48) + b"\x00"


def test_the_volume_column_states_a_position_across_the_field_as_well_as_a_level() -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(volume=VolumeCommand(effect=VolumeEffect.PANNING, amount=32)))
    pattern = builder.build()
    assert rebuilt(pattern, channels=1) == pattern


def test_a_cut_is_the_one_command_this_column_carries() -> None:
    builder = PatternBuilder(rows=2, channels=1)
    builder.place(0, 0, Cell(note=Note(60), instrument=0))
    builder.place(1, 0, Cell(note=NoteCommand.CUT))
    pattern = builder.build()
    assert rebuilt(pattern, channels=1) == pattern


def test_a_byte_this_column_leaves_unnamed_reads_as_absent() -> None:
    block = pattern_block((cell_bytes(0, note=0x9F, sample=1),))
    cursor = Cursor(block)
    with pytest.warns(UserWarning, match="unnamed"):
        pattern = unpack_pattern(cursor, rows=PATTERN_ROWS, channels=1, subject="pattern", repairs=Repairs())

    assert pattern.cell(0, 0) == Cell(instrument=0)


def test_cells_on_channels_past_the_stated_width_read_as_silence() -> None:
    block = pattern_block(
        (cell_bytes(0, note=REFERENCE_BYTE, sample=1) + cell_bytes(6, note=REFERENCE_BYTE, sample=1),)
    )
    repairs = Repairs()
    pattern = unpack_pattern(Cursor(block), rows=PATTERN_ROWS, channels=2, subject="pattern", repairs=repairs)
    assert pattern.channels == 2
    assert [repair for _, repair in repairs.entries] == ["1 cells on channels past the 2 stated read as silence"]


def test_a_stream_ending_early_leaves_the_rows_it_never_reached_silent() -> None:
    block = pattern_block((cell_bytes(0, note=REFERENCE_BYTE, sample=1),))[: 2 + 4]
    repairs = Repairs()
    pattern = unpack_pattern(Cursor(block), rows=PATTERN_ROWS, channels=1, subject="pattern", repairs=repairs)
    assert pattern.rows == PATTERN_ROWS
    assert [repair for _, repair in repairs.entries] == ["63 rows past the end of the stream read as silence"]
    with pytest.warns(RepairWarning):
        repairs.warn()


def test_a_block_whose_length_leaves_out_its_own_field_reads_to_the_same_music() -> None:
    # The trackers of this lineage counted the length both ways, so the row terminators are what
    # delimit the cells and the stated length is read as the room they have.
    block = pattern_block((cell_bytes(0, note=REFERENCE_BYTE, sample=1),))
    shortened = (len(block) - 2).to_bytes(2, "little") + block[2:]
    repairs = Repairs()
    counted = unpack_pattern(Cursor(block), rows=PATTERN_ROWS, channels=1, subject="a", repairs=repairs)
    excluded = unpack_pattern(Cursor(shortened), rows=PATTERN_ROWS, channels=1, subject="b", repairs=repairs)
    assert counted == excluded


def test_a_cell_naming_a_sample_and_no_key_reads_back_as_the_sample_alone() -> None:
    block = pattern_block((cell_bytes(0, note=ABSENT_NOTE, sample=3),))
    pattern = unpack_pattern(Cursor(block), rows=PATTERN_ROWS, channels=1, subject="pattern", repairs=Repairs())
    assert pattern.cell(0, 0) == Cell(instrument=2)


def test_a_volume_byte_this_column_leaves_unnamed_reads_as_absent() -> None:
    block = pattern_block((cell_bytes(0, note=REFERENCE_BYTE, sample=1, volume=100),))
    with pytest.warns(UserWarning, match="unnamed"):
        pattern = unpack_pattern(Cursor(block), rows=PATTERN_ROWS, channels=1, subject="pattern", repairs=Repairs())

    assert pattern.cell(0, 0) == Cell(note=Note(60), instrument=0)


def test_a_command_stating_nothing_carries_no_effect() -> None:
    block = pattern_block((cell_bytes(0, note=REFERENCE_BYTE, sample=1, command=0, parameter=0),))
    pattern = unpack_pattern(Cursor(block), rows=PATTERN_ROWS, channels=1, subject="pattern", repairs=Repairs())
    assert pattern.cell(0, 0).effect is None

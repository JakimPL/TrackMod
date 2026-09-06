import numpy as np
import pytest

from tests.trackers.mod.conftest import cell_bytes, mod_pattern
from trackmod.binary.cursor import Cursor
from trackmod.binary.warnings import UnnamedByteWarning
from trackmod.core.notes.command import NoteCommand
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.grid import Pattern
from trackmod.core.repairs.report import Repairs
from trackmod.core.volumes.command import VolumeCommand, VolumeEffect
from trackmod.spec.pitch import RATE_NOTE
from trackmod.trackers.amiga.note import PERIODS
from trackmod.trackers.amiga.patterns.packer import encode_cell, pack_pattern
from trackmod.trackers.amiga.patterns.parser import unpack_cells, unpack_pattern
from trackmod.trackers.amiga.patterns.sizing import packed_bytes
from trackmod.trackers.amiga.spec.cells import CELL_BYTES
from trackmod.trackers.amiga.spec.ranges import PATTERN_ROWS
from trackmod.trackers.mod.effects.catalog import MOD_EFFECTS
from trackmod.trackers.mod.spec.ranges import CANONICAL_CHANNELS

SAMPLES = 3


def rebuilt(pattern: Pattern) -> Pattern:
    """The grid a packed pattern reads back as, through the cursor a reader walks the file with.

    Nothing is repaired on the way, because a round trip that repaired its way to equality is one that
    lost something and put silence in its place.
    """
    repairs = Repairs()
    cursor = Cursor(pack_pattern(pattern))
    grid = unpack_pattern(
        cursor,
        rows=pattern.rows,
        channels=pattern.channels,
        subject="pattern",
        repairs=repairs,
    )
    assert repairs.entries == ()
    return grid


def test_a_pattern_reads_back_as_it_was_written() -> None:
    pattern = mod_pattern(channels=CANONICAL_CHANNELS, samples=SAMPLES, seed=3)
    assert rebuilt(pattern) == pattern


def test_the_size_model_is_the_packer_counted_rather_than_run() -> None:
    pattern = mod_pattern(channels=CANONICAL_CHANNELS, samples=SAMPLES, seed=4)
    assert packed_bytes(pattern) == len(pack_pattern(pattern))


def test_silence_costs_exactly_what_music_costs() -> None:
    # Nothing here is packed, so a pattern's length says nothing about what it holds — which is why the
    # format needs no length field anywhere and a reader can seek to any pattern by multiplying.
    empty = Pattern.empty(rows=PATTERN_ROWS, channels=CANONICAL_CHANNELS)
    played = mod_pattern(channels=CANONICAL_CHANNELS, samples=SAMPLES, seed=5)
    assert packed_bytes(empty) == packed_bytes(played)
    assert packed_bytes(empty) == PATTERN_ROWS * CANONICAL_CHANNELS * CELL_BYTES


def test_the_sample_number_is_split_across_the_two_high_nibbles() -> None:
    written = encode_cell(RATE_NOTE, 30, -1, -1, -1)
    assert written[0] >> 4 == 31 >> 4
    assert written[2] >> 4 == 31 & 0x0F
    assert ((written[0] & 0x0F) << 8) | written[1] == PERIODS[RATE_NOTE]


def test_a_cell_stating_a_volume_is_refused() -> None:
    with pytest.raises(ValueError, match="carry note, sample and effect only"):
        encode_cell(RATE_NOTE, 0, 32, -1, -1)


def test_a_pattern_stating_a_volume_command_is_refused() -> None:
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=1)
    builder.place(0, 0, Cell(volume=VolumeCommand(effect=VolumeEffect.PORTAMENTO, amount=4)))
    with pytest.raises(ValueError, match="volume"):
        pack_pattern(builder.build())


def test_an_effect_command_past_four_bits_is_refused() -> None:
    with pytest.raises(ValueError, match="four bits"):
        encode_cell(-1, -1, -1, 20, 0)


def test_a_note_command_is_refused_where_the_column_holds_a_period() -> None:
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=1)
    builder.place(0, 0, Cell(note=NoteCommand.OFF))
    with pytest.raises(ValueError, match="stores a period"):
        pack_pattern(builder.build())


def test_a_cell_carrying_only_an_effect_keeps_it() -> None:
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=1)
    builder.place(2, 0, Cell(effect=MOD_EFFECTS.set_speed(4)))
    pattern = builder.build()
    assert rebuilt(pattern) == pattern


def test_a_period_no_key_sounds_reads_as_absent() -> None:
    stream = cell_bytes(period=2, sample=1) + bytes(CELL_BYTES * 3)
    with pytest.warns(UnnamedByteWarning, match="note 2"):
        pattern = unpack_cells(stream, rows=1, channels=4, subject="pattern 0", repairs=Repairs())

    assert pattern.cell(0, 0).note is None
    assert pattern.cell(0, 0).instrument == 0


def test_a_period_a_digit_off_is_drawn_to_the_key_it_comes_closest_to() -> None:
    repairs = Repairs()
    stream = cell_bytes(period=PERIODS[RATE_NOTE] + 1) + bytes(CELL_BYTES * 3)
    pattern = unpack_cells(stream, rows=1, channels=4, subject="pattern 0", repairs=repairs)
    assert pattern.cell(0, 0).note == Note(RATE_NOTE)
    assert repairs.entries == (("pattern 0", "1 periods read as the key they come closest to"),)


def test_cells_past_the_end_of_the_file_read_as_silence() -> None:
    repairs = Repairs()
    stream = cell_bytes(period=PERIODS[RATE_NOTE], sample=1)
    pattern = unpack_cells(stream, rows=2, channels=2, subject="pattern 0", repairs=repairs)
    assert pattern.cell(0, 0).note == Note(RATE_NOTE)
    assert not np.any(pattern.occupied[1])
    assert repairs.entries == (("pattern 0", "3 cells past the end of the file read as silence"),)

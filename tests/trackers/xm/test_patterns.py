import warnings

import pytest

from tests.trackers.xm.conftest import xm_pattern
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
from trackmod.spec.grid import EMPTY
from trackmod.spec.pitch import NOTE_COUNT
from trackmod.trackers.xm.note import stored_note
from trackmod.trackers.xm.patterns.packer import pack_cells
from trackmod.trackers.xm.patterns.parser import unpack_cells
from trackmod.trackers.xm.patterns.sizing import packed_bytes
from trackmod.trackers.xm.spec.cells import (
    KEY_OFF,
    PACKED_BYTE,
    RAW_CELL_BYTES,
    VOLUME_COLUMN_BASE,
    VOLUME_COLUMN_EMPTY,
    CellMask,
)
from trackmod.trackers.xm.spec.ranges import MAX_ROWS
from trackmod.trackers.xm.spec.volume import VOLUME_COLUMN

GRIDS = (
    (16, 4, 2, 1),
    (64, 12, 3, 2),
    (MAX_ROWS, 16, 4, 3),
    (1, 1, 1, 4),
)


SUBJECT = "pattern 0"


@pytest.mark.parametrize("rows,channels,instruments,seed", GRIDS, ids=lambda value: str(value))
def test_the_size_model_agrees_with_the_packer_byte_for_byte(
    rows: int, channels: int, instruments: int, seed: int
) -> None:
    pattern = xm_pattern(rows=rows, channels=channels, instruments=instruments, seed=seed)
    assert packed_bytes(pattern) == len(pack_cells(pattern))


@pytest.mark.parametrize("rows,channels,instruments,seed", GRIDS, ids=lambda value: str(value))
def test_a_packed_pattern_unpacks_to_the_same_grid(rows: int, channels: int, instruments: int, seed: int) -> None:
    pattern = xm_pattern(rows=rows, channels=channels, instruments=instruments, seed=seed)
    assert (
        unpack_cells(pack_cells(pattern), rows=rows, channels=channels, subject=SUBJECT, repairs=Repairs()) == pattern
    )


def test_a_silent_channel_still_costs_the_byte_that_holds_its_place() -> None:
    # There is no row terminator and no way to skip a channel, so a player reads exactly one cell per
    # grid position and an empty one is the bare mask.
    empty = Pattern.empty(rows=8, channels=16)
    stream = pack_cells(empty)
    assert len(stream) == PACKED_BYTE * empty.rows * empty.channels
    assert set(stream) == {int(CellMask.PACKED)}


def test_a_cell_stating_every_column_drops_its_mask() -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(note=Note(60), instrument=0, volume=32, effect=Effect(command=15, parameter=6)))
    stream = pack_cells(builder.build())
    assert len(stream) == RAW_CELL_BYTES
    assert stream[0] == stored_note(60)
    assert not stream[0] & CellMask.PACKED


def test_a_partial_cell_pays_a_mask_and_a_byte_for_each_column_it_states() -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(note=Note(60), volume=32))
    stream = pack_cells(builder.build())
    assert stream[0] == CellMask.PACKED | CellMask.NOTE | CellMask.VOLUME
    assert stream[1] == stored_note(60)
    assert stream[2] == VOLUME_COLUMN_BASE + 32
    assert len(stream) == 3


def test_the_format_keeps_no_memory_so_a_repeated_cell_costs_the_same_every_row() -> None:
    builder = PatternBuilder(rows=4, channels=1)
    for row in range(4):
        builder.place(row, 0, Cell(note=Note(60), instrument=0, volume=32))

    assert len(pack_cells(builder.build())) == 4 * (1 + 3)


def test_a_key_off_survives_a_round_trip() -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(note=NoteCommand.OFF))
    recovered = unpack_cells(pack_cells(builder.build()), rows=1, channels=1, subject=SUBJECT, repairs=Repairs())
    assert recovered.cell(0, 0) == Cell(note=NoteCommand.OFF)


@pytest.mark.parametrize("command", [NoteCommand.CUT, NoteCommand.FADE])
def test_a_note_command_the_column_cannot_state_is_refused(command: NoteCommand) -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(note=command))
    with pytest.raises(ValueError):
        pack_cells(builder.build())


def test_a_key_above_the_octaves_this_format_numbers_is_refused() -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(note=Note(NOTE_COUNT - 1)))
    with pytest.raises(ValueError):
        pack_cells(builder.build())


def test_a_volume_column_effect_is_read_as_the_command_it_states() -> None:
    # 0x60 opens the column's own slide range, which the shared model now holds as a command.
    recovered = unpack_cells_at(volume_stream(0x60))
    assert recovered.cell(0, 0).volume == VolumeCommand(effect=VolumeEffect.VOLUME_SLIDE_DOWN, amount=0)


def test_the_byte_a_cell_writes_for_no_volume_states_an_absence() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        recovered = unpack_cells_at(volume_stream(VOLUME_COLUMN_EMPTY))

    assert recovered.cell(0, 0).volume is None


UNNAMED_EFFECT = VolumeEffect.PITCH_SLIDE_UP
UNNAMED_BYTE = 0x05


def volume_stream(byte: int) -> bytes:
    """One packed cell stating only a volume."""
    return bytes([CellMask.PACKED | CellMask.VOLUME, byte])


def unpack_cells_at(stream: bytes) -> Pattern:
    """The one-cell pattern a stream packs to."""
    return unpack_cells(stream, rows=1, channels=1, subject=SUBJECT, repairs=Repairs())


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
    assert VOLUME_COLUMN.stored_code(EMPTY) == EMPTY


def test_a_note_byte_the_column_leaves_unnamed_reads_as_absent_and_is_reported() -> None:
    # This format numbers eight octaves from one and keeps 97 for a key off; above that names nothing.
    stream = bytes([CellMask.PACKED | CellMask.NOTE, 120])
    with pytest.warns(UnnamedByteWarning, match="120"):
        recovered = unpack_cells_at(stream)

    assert recovered.cell(0, 0) == Cell()


def test_the_key_off_this_column_keeps_still_reads() -> None:
    stream = bytes([CellMask.PACKED | CellMask.NOTE, KEY_OFF])
    assert unpack_cells_at(stream).cell(0, 0) == Cell(note=NoteCommand.OFF)


def test_a_stream_ending_before_the_grid_does_leaves_the_rest_silent() -> None:
    # Files in the wild carry a pattern whose stream runs out, and a player sounds what is there.
    builder = PatternBuilder(rows=2, channels=2)
    builder.place(0, 0, Cell(note=Note(60), instrument=0, volume=64))
    stream = pack_cells(builder.build())
    repairs = Repairs()
    recovered = unpack_cells(stream[:1], rows=2, channels=2, subject=SUBJECT, repairs=repairs)

    assert recovered.rows == 2
    assert recovered.channels == 2
    assert recovered.cell(1, 1) == Cell()
    assert repairs.entries == ((SUBJECT, "3 cells past the end of the stream read as silence"),)

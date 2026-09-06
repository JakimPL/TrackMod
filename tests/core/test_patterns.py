import numpy as np
import pytest

from trackmod.core.effects.effect import Effect
from trackmod.core.notes.command import NoteCommand
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.column import Column
from trackmod.core.patterns.grid import Pattern
from trackmod.core.volumes.command import VolumeCommand, VolumeEffect
from trackmod.spec.grid import EMPTY, GRID_DTYPE
from trackmod.spec.width import BYTE_MAX

CELLS = (
    Cell(),
    Cell(note=Note(60)),
    Cell(note=NoteCommand.OFF),
    Cell(note=Note(48), instrument=3, volume=64),
    Cell(volume=0),
    Cell(effect=Effect(command=0x0F, parameter=125)),
    Cell(note=Note(72), instrument=0, volume=32, effect=Effect(command=0x0E, parameter=0xD3)),
    Cell(volume=VolumeCommand(effect=VolumeEffect.VIBRATO_DEPTH, amount=4)),
    Cell(note=Note(55), instrument=1, volume=VolumeCommand(effect=VolumeEffect.PANNING, amount=64)),
)


@pytest.mark.parametrize("cell", CELLS, ids=range(len(CELLS)))
def test_a_placed_cell_reads_back_unchanged(cell: Cell) -> None:
    builder = PatternBuilder(rows=4, channels=2)
    builder.place(2, 1, cell)
    assert builder.read(2, 1) == cell
    assert builder.build().cell(2, 1) == cell


def test_a_fresh_grid_is_entirely_absent() -> None:
    pattern = Pattern.empty(rows=3, channels=5)
    assert pattern.rows == 3
    assert pattern.channels == 5
    assert not pattern.occupied.any()
    assert all(np.all(plane == EMPTY) for plane in pattern.columns.values())


def test_volume_zero_is_a_present_cell_not_an_absent_one() -> None:
    # A silent-but-triggered cell is what the volume column stores as 0; absence is a separate state.
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(volume=0))
    pattern = builder.build()
    assert pattern.occupied[0, 0]
    assert pattern.cell(0, 0).volume == 0


def test_a_volume_column_command_occupies_its_position_like_a_level() -> None:
    # The column holds either a level or a command, so both make the cell present.
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(volume=VolumeCommand(effect=VolumeEffect.VOLUME_SLIDE_UP, amount=3)))
    pattern = builder.build()
    assert pattern.occupied[0, 0]
    assert pattern.cell(0, 0).volume == VolumeCommand(effect=VolumeEffect.VOLUME_SLIDE_UP, amount=3)


def test_a_command_and_a_level_stay_apart_in_the_volume_plane() -> None:
    builder = PatternBuilder(rows=2, channels=1)
    builder.place(0, 0, Cell(volume=9))
    builder.place(1, 0, Cell(volume=VolumeCommand(effect=VolumeEffect.FINE_VOLUME_UP, amount=9)))
    pattern = builder.build()
    assert pattern.volume[0, 0] != pattern.volume[1, 0]


def test_a_note_only_cell_occupies_its_position() -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(note=NoteCommand.OFF))
    assert builder.build().occupied[0, 0]


def test_placing_replaces_every_column() -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(note=Note(60), instrument=2, volume=48, effect=Effect(command=1, parameter=2)))
    builder.place(0, 0, Cell(note=Note(61)))
    assert builder.read(0, 0) == Cell(note=Note(61))


def test_free_effect_channel_finds_the_lowest_open_slot() -> None:
    builder = PatternBuilder(rows=1, channels=3)
    assert builder.free_effect_channel(0) == 0
    builder.place(0, 0, Cell(effect=Effect(command=1, parameter=0)))
    assert builder.free_effect_channel(0) == 1
    for channel in (1, 2):
        builder.place(0, channel, Cell(effect=Effect(command=1, parameter=0)))

    assert builder.free_effect_channel(0) is None


def test_a_note_without_an_effect_leaves_the_effect_slot_free() -> None:
    builder = PatternBuilder(rows=1, channels=2)
    builder.place(0, 0, Cell(note=Note(60), volume=64))
    assert builder.free_effect_channel(0) == 0


def test_building_snapshots_the_grid() -> None:
    builder = PatternBuilder(rows=1, channels=1)
    builder.place(0, 0, Cell(note=Note(60)))
    pattern = builder.build()
    builder.place(0, 0, Cell(note=Note(61)))
    assert pattern.cell(0, 0) == Cell(note=Note(60))


def test_placing_outside_the_grid_raises() -> None:
    builder = PatternBuilder(rows=2, channels=2)
    with pytest.raises(IndexError):
        builder.place(2, 0, Cell(note=Note(60)))


def test_columns_of_different_shapes_are_rejected() -> None:
    columns = {column: np.full((2, 2), EMPTY, dtype=GRID_DTYPE) for column in Column}
    columns[Column.VOLUME] = np.full((2, 3), EMPTY, dtype=GRID_DTYPE)
    with pytest.raises(ValueError):
        Pattern.from_columns(columns)


@pytest.mark.parametrize("column", [Column.EFFECT, Column.PARAMETER])
@pytest.mark.parametrize("value", [BYTE_MAX + 1, EMPTY - 1])
def test_an_effect_past_the_byte_a_cell_states_it_in_is_rejected(column: Column, value: int) -> None:
    # A cell holds both in one byte and every format writes them as one, so a grid built from planes is
    # held to the same reach as one built cell by cell, where the model states it already.
    columns = {name: np.full((2, 2), EMPTY, dtype=GRID_DTYPE) for name in Column}
    columns[column] = np.full((2, 2), value, dtype=GRID_DTYPE)
    with pytest.raises(ValueError, match="one byte"):
        Pattern.from_columns(columns)


@pytest.mark.parametrize("column", [Column.EFFECT, Column.PARAMETER])
def test_an_effect_filling_the_byte_a_cell_states_it_in_is_kept(column: Column) -> None:
    columns = {name: np.full((2, 2), EMPTY, dtype=GRID_DTYPE) for name in Column}
    columns[column] = np.full((2, 2), BYTE_MAX, dtype=GRID_DTYPE)
    assert int(Pattern.from_columns(columns).column(column).max()) == BYTE_MAX


def test_a_one_dimensional_column_is_rejected() -> None:
    columns = {column: np.full((2, 2), EMPTY, dtype=GRID_DTYPE) for column in Column}
    columns[Column.NOTE] = np.full(4, EMPTY, dtype=GRID_DTYPE)
    with pytest.raises(ValueError):
        Pattern.from_columns(columns)


@pytest.mark.parametrize("size", [(0, 4), (4, 0)])
def test_an_empty_grid_is_rejected(size: tuple[int, int]) -> None:
    rows, channels = size
    with pytest.raises(ValueError):
        Pattern.empty(rows=rows, channels=channels)


def test_widening_pads_with_silent_channels() -> None:
    builder = PatternBuilder(rows=2, channels=1)
    builder.place(0, 0, Cell(note=Note(60)))
    widened = builder.build().widened(3)
    assert widened.channels == 3
    assert widened.cell(0, 0) == Cell(note=Note(60))
    assert widened.cell(0, 2) == Cell()


def test_narrowing_is_refused() -> None:
    with pytest.raises(ValueError):
        Pattern.empty(rows=2, channels=4).widened(2)


def test_grids_compare_by_their_contents() -> None:
    builder = PatternBuilder(rows=2, channels=1)
    builder.place(0, 0, Cell(note=Note(60)))
    first, second = builder.build(), builder.build()
    assert first == second
    assert hash(first) == hash(second)
    assert first != Pattern.empty(rows=2, channels=1)

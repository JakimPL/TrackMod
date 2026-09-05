from trackmod.binary.cursor import Cursor
from trackmod.binary.warnings import UnnamedBytes
from trackmod.core.effects.effect import Effect
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.column import Column
from trackmod.core.patterns.grid import Pattern
from trackmod.core.repairs.report import Repairs
from trackmod.trackers.mod.note import PERIODS, decode_period
from trackmod.trackers.mod.spec.cells import (
    CELL_BYTES,
    COMMAND_MASK,
    NO_EFFECT,
    NO_PERIOD,
    NO_SAMPLE,
    PERIOD_HIGH_BITS,
    PERIOD_HIGH_MASK,
    SAMPLE_HIGH_MASK,
    SAMPLE_OFFSET,
    SAMPLE_SHIFT,
)


class StatedPeriods:
    """The periods one pattern stated, counted so a pattern reports what it drew to a key once.

    Every tracker of this lineage wrote its own table and they disagree in the last digit, so a period
    is read as the key it comes closest to. That draws a value the model holds no room for into one it
    does, which is a repair, and a pattern full of them says so once.
    """

    def __init__(self) -> None:
        self._drawn = 0

    def stated(self, period: int, unnamed: UnnamedBytes) -> Note | None:
        """The key a stored period sounds, recording a period that lands on no key this format holds."""
        note = decode_period(period)
        if note is None:
            unnamed.met(period, column=Column.NOTE)
        elif PERIODS[note.value] != period:
            self._drawn += 1

        return note

    @property
    def drawn(self) -> int:
        """How many periods were read as the key they came closest to."""
        return self._drawn


def decode_effect(command: int, parameter: int) -> Effect | None:
    """The effect a cell carries, which an empty command with an empty parameter does not."""
    if command == NO_EFFECT and parameter == NO_EFFECT:
        return None

    return Effect(command=command, parameter=parameter)


def decode_cell(cell: bytes, periods: StatedPeriods, unnamed: UnnamedBytes) -> Cell:
    """One cell, read from the four bytes that hold it."""
    period = ((cell[0] & PERIOD_HIGH_MASK) << PERIOD_HIGH_BITS) | cell[1]
    sample = (cell[0] & SAMPLE_HIGH_MASK) | (cell[2] >> SAMPLE_SHIFT)
    return Cell(
        note=None if period == NO_PERIOD else periods.stated(period, unnamed),
        instrument=None if sample == NO_SAMPLE else sample - SAMPLE_OFFSET,
        effect=decode_effect(cell[2] & COMMAND_MASK, cell[3]),
    )


def unpack_cells(stream: bytes, *, rows: int, channels: int, subject: str, repairs: Repairs) -> Pattern:
    """Rebuild a pattern grid from a stored run of fixed cells.

    A run ending before the grid does leaves the rest of the grid silent, which is what a player sounds
    where the cells run out.
    """
    unnamed = UnnamedBytes()
    periods = StatedPeriods()
    builder = PatternBuilder(rows=rows, channels=channels)
    held = len(stream) // CELL_BYTES
    for placed in range(min(held, rows * channels)):
        offset = placed * CELL_BYTES
        builder.place(
            placed // channels,
            placed % channels,
            decode_cell(stream[offset : offset + CELL_BYTES], periods, unnamed),
        )

    missing = rows * channels - held
    if missing > 0:
        repairs.made(f"{missing} cells past the end of the file read as silence", subject=subject)

    if periods.drawn:
        repairs.made(f"{periods.drawn} periods read as the key they come closest to", subject=subject)

    unnamed.warn()
    return builder.build()


def unpack_pattern(cursor: Cursor, *, rows: int, channels: int, subject: str, repairs: Repairs) -> Pattern:
    """Read one pattern from the cursor's position, which is every cell of a fixed grid and no header."""
    stream = cursor.take_at_most(rows * channels * CELL_BYTES)
    return unpack_cells(stream, rows=rows, channels=channels, subject=subject, repairs=repairs)

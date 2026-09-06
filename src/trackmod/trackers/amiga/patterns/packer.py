from trackmod.core.patterns.grid import Pattern
from trackmod.spec.grid import EMPTY
from trackmod.spec.width import BYTE_MAX, NIBBLE_MAX
from trackmod.trackers.amiga.note import stored_note
from trackmod.trackers.amiga.spec.cells import (
    COMMAND_MASK,
    NO_EFFECT,
    NO_PERIOD,
    NO_SAMPLE,
    PERIOD_HIGH_BITS,
    SAMPLE_HIGH_MASK,
    SAMPLE_OFFSET,
    SAMPLE_SHIFT,
)


def stored_sample(instrument: int) -> int:
    """The sample number a cell states, which is one above the shared numbering.

    Zero is what a cell writes to leave the channel on the sample it already plays.
    """
    return NO_SAMPLE if instrument == EMPTY else instrument + SAMPLE_OFFSET


def stated_effect(command: int, parameter: int) -> tuple[int, int]:
    """The command nibble and parameter byte a cell writes.

    Raises:
        ValueError: when the command needs more than the four bits a cell holds for it.
    """
    stated, argument = max(command, NO_EFFECT), max(parameter, NO_EFFECT)
    if stated > NIBBLE_MAX:
        raise ValueError(f"effect command {stated} needs more than the four bits a cell holds")

    return stated, argument


def reject_volume(volume: int) -> None:
    """Refuse a cell this lineage has no column for.

    Raises:
        ValueError: when the cell states a volume, which this lineage's cells have no column for.
    """
    if volume != EMPTY:
        raise ValueError("a cell states a volume, and this format's cells carry note, sample and effect only")


def encode_cell(note: int, instrument: int, volume: int, command: int, parameter: int) -> bytes:
    """The four bytes one grid position is written as.

    The sample number is split across the two high nibbles of the cell, and the period fills the twelve
    bits left between them, which is what makes a cell exactly four bytes with no mask anywhere.
    """
    reject_volume(volume)
    stated = stored_note(note)
    period = NO_PERIOD if stated == EMPTY else stated
    sample = stored_sample(instrument)
    effect, argument = stated_effect(command, parameter)
    return bytes(
        (
            (sample & SAMPLE_HIGH_MASK) | (period >> PERIOD_HIGH_BITS),
            period & BYTE_MAX,
            ((sample & NIBBLE_MAX) << SAMPLE_SHIFT) | (effect & COMMAND_MASK),
            argument,
        )
    )


def pack_cells(pattern: Pattern) -> bytes:
    """Serialise a pattern grid into this lineage's stream of fixed cells."""
    notes, instruments = pattern.note, pattern.instrument
    volumes, commands, parameters = pattern.volume, pattern.effect, pattern.parameter

    stream = bytearray()
    for row in range(pattern.rows):
        for channel in range(pattern.channels):
            stream += encode_cell(
                int(notes[row, channel]),
                int(instruments[row, channel]),
                int(volumes[row, channel]),
                int(commands[row, channel]),
                int(parameters[row, channel]),
            )

    return bytes(stream)


def pack_pattern(pattern: Pattern) -> bytes:
    """Serialise a pattern, which is its cells and nothing else — this lineage writes no pattern header."""
    return pack_cells(pattern)

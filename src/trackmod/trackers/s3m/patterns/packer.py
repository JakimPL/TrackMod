from trackmod.core.patterns.grid import Pattern
from trackmod.spec.grid import EMPTY
from trackmod.trackers.s3m.layout.pattern import PATTERN_HEADER
from trackmod.trackers.s3m.note import stored_note
from trackmod.trackers.s3m.spec.cells import (
    END_OF_ROW,
    NO_EFFECT,
    NO_SAMPLE,
    SAMPLE_OFFSET,
    CellMask,
    NoteByte,
)
from trackmod.trackers.s3m.spec.sizes import PATTERN_LENGTH_BYTES
from trackmod.trackers.s3m.volume import stored_volume


def stored_sample(instrument: int) -> int:
    """The sample number a cell states, which is one above the shared numbering.

    Zero is what a cell writes to leave the channel on the sample it already plays.
    """
    return NO_SAMPLE if instrument == EMPTY else instrument + SAMPLE_OFFSET


def key_bytes(note: int, instrument: int) -> bytes:
    """The two bytes a cell's first group holds: the key it presses and the sample that sounds it."""
    stated = stored_note(note)
    return bytes((NoteByte.ABSENT if stated == EMPTY else stated, stored_sample(instrument)))


def effect_bytes(command: int, parameter: int) -> bytes:
    """The two bytes a cell's effect group holds, which a byte apiece is room enough for."""
    return bytes((max(command, NO_EFFECT), max(parameter, NO_EFFECT)))


def encode_cell(note: int, instrument: int, volume: int, command: int, parameter: int) -> tuple[int, bytes]:
    """The marker one grid position contributes and the groups of bytes that follow it.

    A cell states its key and its sample together, because the two share one marker bit, and states
    nothing at all where every column is absent.
    """
    marker = 0
    payload = bytearray()
    if note != EMPTY or instrument != EMPTY:
        marker |= CellMask.KEY
        payload += key_bytes(note, instrument)

    if volume != EMPTY:
        marker |= CellMask.VOLUME
        payload.append(stored_volume(volume))

    if command != EMPTY:
        marker |= CellMask.EFFECT
        payload += effect_bytes(command, parameter)

    return marker, bytes(payload)


def pack_cells(pattern: Pattern) -> bytes:
    """Serialise a pattern grid into this format's channel-marker byte stream.

    A row names only the channels that carry something and closes with a zero byte, so a silent channel
    costs nothing and a silent row costs the one byte that ends it.
    """
    notes, instruments = pattern.note, pattern.instrument
    volumes, commands, parameters = pattern.volume, pattern.effect, pattern.parameter
    occupied = pattern.occupied

    stream = bytearray()
    for row in range(pattern.rows):
        for channel in range(pattern.channels):
            if not occupied[row, channel]:
                continue

            marker, payload = encode_cell(
                int(notes[row, channel]),
                int(instruments[row, channel]),
                int(volumes[row, channel]),
                int(commands[row, channel]),
                int(parameters[row, channel]),
            )
            stream.append(marker | channel)
            stream += payload

        stream.append(END_OF_ROW)

    return bytes(stream)


def pack_pattern(pattern: Pattern) -> bytes:
    """Serialise a pattern: the length of the whole block, then the packed cell stream."""
    stream = pack_cells(pattern)
    header = PATTERN_HEADER.pack({"block_size": PATTERN_LENGTH_BYTES + len(stream)})
    return header + stream

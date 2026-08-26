from typing import Final

import numpy as np
from numpy.typing import NDArray

from trackmod.binary.bits import BitReader
from trackmod.core.samples.depth import BitDepth
from trackmod.spec.width import BITS_PER_BYTE

BLOCK_LENGTH_BYTES: Final = 2
BLOCK_FRAMES: Final[dict[BitDepth, int]] = {BitDepth.EIGHT: 0x8000, BitDepth.SIXTEEN: 0x4000}

_NARROW_WIDTH: Final = 7  # the widths below which a field of its own announces the next one
_NARROW_BITS: Final[dict[BitDepth, int]] = {BitDepth.EIGHT: 3, BitDepth.SIXTEEN: 4}
_SPREAD: Final[dict[BitDepth, int]] = {BitDepth.EIGHT: 4, BitDepth.SIXTEEN: 8}
_STORED_DTYPES: Final[dict[BitDepth, type[np.signedinteger]]] = {BitDepth.EIGHT: np.int8, BitDepth.SIXTEEN: np.int16}


def _widened(stated: int, width: int) -> int:
    """The width a value announcing one names, which skips the width it was announced at."""
    return stated if stated < width else stated + 1


def _announced(width: int, bits: int) -> int:
    """A width a block announces, held to what a frame of its depth reads.

    Raises:
        ValueError: when the announced width names more bits than a frame holds, or none at all.
    """
    if not 1 <= width <= bits + 1:
        raise ValueError(f"a compressed block announces width {width}, past the {bits} bits its frames hold")

    return width


def _signed(value: int, *, width: int, depth: BitDepth) -> int:
    """A field read at ``width`` bits, as the signed amplitude its depth stores.

    A field narrower than the depth carries its sign in its own top bit; one as wide as the depth or
    wider carries it in the depth's, which is where a field opening one bit wide of its depth lands once
    the widths it could have announced are past.
    """
    bits = int(depth)
    if width < bits:
        return value - (1 << width) if value & (1 << (width - 1)) else value

    stored = value & ((1 << bits) - 1)
    return stored - (1 << bits) if stored & (1 << (bits - 1)) else stored


def _block_frames(reader: BitReader, count: int, *, depth: BitDepth) -> list[int]:
    """The frames one compressed block holds, read as the differences a player sums.

    A block opens at one bit wider than its depth and narrows as the waveform allows. Three ranges of the
    field announce a new width instead of carrying a value -- one for the narrowest widths, one for the
    middle, and one for the widest -- so the width travels in the stream beside the values it reads.

    Raises:
        ValueError: when the stream announces a width past what the depth holds.
    """
    bits = int(depth)
    spread = _SPREAD[depth]
    width = bits + 1
    frames: list[int] = []
    while len(frames) < count:
        value = reader.take(width)
        if width < _NARROW_WIDTH:
            if value == 1 << (width - 1):
                width = _announced(_widened(reader.take(_NARROW_BITS[depth]) + 1, width), bits)
                continue
        elif width < bits + 1:
            high = (((1 << bits) - 1) >> (bits + 1 - width)) + spread
            if high - 2 * spread < value <= high:
                width = _announced(_widened(value - (high - 2 * spread), width), bits)
                continue
        elif value & (1 << bits):
            width = _announced((value + 1) & ((1 << BITS_PER_BYTE) - 1), bits)
            continue

        frames.append(_signed(value, width=width, depth=depth))

    return frames


def decompress(data: bytes, *, frames: int, depth: BitDepth, doubled: bool) -> NDArray[np.int64]:
    """The waveform a block-compressed sample holds, as the stored integers its frames sit on.

    Impulse Tracker stores a long waveform in blocks, each opening with the byte count that follows it,
    and each block's fields are the differences of a running sum. Version 2.15 sums twice, which carries
    a smoother waveform in narrower fields, and ``doubled`` is what the file's own compatibility version
    states about which sum was written.
    """
    dtype = _STORED_DTYPES[depth]
    written = 0
    position = 0
    blocks: list[NDArray[np.int64]] = []
    while written < frames:
        length = int.from_bytes(data[position : position + BLOCK_LENGTH_BYTES], "little")
        position += BLOCK_LENGTH_BYTES
        count = min(BLOCK_FRAMES[depth], frames - written)
        reader = BitReader(data[position : position + length])
        position += length
        stated = np.asarray(_block_frames(reader, count, depth=depth), dtype=dtype)
        summed = np.cumsum(stated, dtype=dtype)
        blocks.append(np.asarray(np.cumsum(summed, dtype=dtype) if doubled else summed, dtype=np.int64))
        written += count

    return np.concatenate(blocks) if blocks else np.zeros(0, dtype=np.int64)

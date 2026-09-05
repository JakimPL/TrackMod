from collections.abc import Iterator
from typing import Final

import numpy as np
from numpy.typing import NDArray

from trackmod.binary.bits import BitReader
from trackmod.core.repairs.report import Repairs
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


def _announced(width: int, bits: int) -> int | None:
    """A width a block announces, or ``None`` when it names more bits than a frame of its depth reads.

    A stream announcing such a width has stopped describing frames, so the block ends where it does.
    """
    return width if 1 <= width <= bits + 1 else None


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

    A width past what a frame of the depth reads ends the block, leaving the frames it would have
    carried for the caller to fill out.
    """
    bits = int(depth)
    spread = _SPREAD[depth]
    width = bits + 1
    frames: list[int] = []
    while len(frames) < count:
        value = reader.take(width)
        stated: int | None = None
        if width < _NARROW_WIDTH:
            if value == 1 << (width - 1):
                stated = _widened(reader.take(_NARROW_BITS[depth]) + 1, width)
        elif width < bits + 1:
            high = (((1 << bits) - 1) >> (bits + 1 - width)) + spread
            if high - 2 * spread < value <= high:
                stated = _widened(value - (high - 2 * spread), width)
        elif value & (1 << bits):
            stated = (value + 1) & ((1 << BITS_PER_BYTE) - 1)

        if stated is not None:
            announced = _announced(stated, bits)
            if announced is None:
                break

            width = announced
            continue

        frames.append(_signed(value, width=width, depth=depth))

    return frames


def _blocks(data: bytes, *, frames: int, depth: BitDepth) -> Iterator[tuple[bytes, int, int]]:
    """Each compressed block a waveform is stored in: its payload, its frames, and where it ends.

    A block opens with the byte count that follows it, so the blocks are walked by their own lengths and
    a caller reading only how far they reach pays nothing for the fields inside them.
    """
    written = 0
    position = 0
    while written < frames:
        length = int.from_bytes(data[position : position + BLOCK_LENGTH_BYTES], "little")
        position += BLOCK_LENGTH_BYTES
        count = min(BLOCK_FRAMES[depth], frames - written)
        yield data[position : position + length], count, position + length
        position += length
        written += count


def compressed_bytes(data: bytes, *, frames: int, depth: BitDepth) -> int:
    """How many bytes a block-compressed waveform occupies, read from the block lengths alone."""
    return max((end for _, _, end in _blocks(data, frames=frames, depth=depth)), default=0)


def decompress(
    data: bytes,
    *,
    frames: int,
    depth: BitDepth,
    doubled: bool,
    subject: str,
    repairs: Repairs,
) -> NDArray[np.int64]:
    """The waveform a block-compressed sample holds, as the stored integers its frames sit on.

    Impulse Tracker stores a long waveform in blocks, and each block's fields are the differences of a
    running sum that restarts with it. Version 2.15 sums twice, which carries a smoother waveform in
    narrower fields, and ``doubled`` is what the file's own compatibility version states about which sum
    was written.

    A block whose stream stops describing frames is filled out with silence, which is what a player
    sounds where the fields run out.
    """
    dtype = _STORED_DTYPES[depth]
    blocks: list[NDArray[np.int64]] = []
    for payload, count, _ in _blocks(data, frames=frames, depth=depth):
        stated = np.asarray(_block_frames(BitReader(payload), count, depth=depth), dtype=dtype)
        summed = np.cumsum(stated, dtype=dtype)
        block = np.asarray(np.cumsum(summed, dtype=dtype) if doubled else summed, dtype=np.int64)
        if block.size < count:
            repairs.made(f"{count - block.size} frames past a block's fields read as silence", subject=subject)
            block = np.concatenate([block, np.zeros(count - block.size, dtype=np.int64)])

        blocks.append(block)

    return np.concatenate(blocks) if blocks else np.zeros(0, dtype=np.int64)

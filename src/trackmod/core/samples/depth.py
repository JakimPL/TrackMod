from enum import IntEnum, unique
from typing import Final

from trackmod.spec.width import BITS_PER_BYTE


@unique
class BitDepth(IntEnum):
    """How many bits one stored frame of PCM occupies.

    A :class:`~trackmod.core.samples.sample.Sample` holds float amplitudes whatever its depth. This is
    the width its frames are written at, and what a format's size model charges for them.

    Example:
        >>> from trackmod import BitDepth
        >>> BitDepth.SIXTEEN.bytes_per_frame
        2
        >>> BitDepth.EIGHT.scale
        128.0
    """

    EIGHT = 8
    SIXTEEN = 16

    @property
    def bytes_per_frame(self) -> int:
        """How many bytes one frame occupies on disk."""
        return self // BITS_PER_BYTE

    @property
    def scale(self) -> float:
        """The full-scale factor that maps float PCM in ``[-1, 1]`` onto the stored integer range."""
        return float(1 << (self - 1))


DEFAULT_DEPTH: Final = BitDepth.SIXTEEN

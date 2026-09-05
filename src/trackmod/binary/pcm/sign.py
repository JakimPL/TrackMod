from enum import StrEnum, unique
from typing import Final

from trackmod.core.samples.depth import BitDepth

NO_BIAS = 0


@unique
class PcmSign(StrEnum):
    """Which stored value a frame of silence sits on.

    Signed storage centres silence on zero, so a frame runs from ``-scale`` to ``scale - 1``. Unsigned
    storage carries the same amplitudes shifted up by ``scale``, so silence sits in the middle of the
    range and every stored value is positive.
    """

    SIGNED = "signed"
    UNSIGNED = "unsigned"


STORED_DTYPES: Final[dict[PcmSign, dict[BitDepth, str]]] = {
    PcmSign.SIGNED: {BitDepth.EIGHT: "<i1", BitDepth.SIXTEEN: "<i2"},
    PcmSign.UNSIGNED: {BitDepth.EIGHT: "<u1", BitDepth.SIXTEEN: "<u2"},
}


def dtype_for(depth: BitDepth, *, sign: PcmSign) -> str:
    """The little-endian numpy dtype one stored frame occupies."""
    return STORED_DTYPES[sign][depth]


def bias(depth: BitDepth, *, sign: PcmSign) -> int:
    """The amount that separates a stored frame from the signed amplitude it carries."""
    match sign:
        case PcmSign.SIGNED:
            return NO_BIAS
        case PcmSign.UNSIGNED:
            return int(depth.scale)

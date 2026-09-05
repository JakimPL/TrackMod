import numpy as np

from trackmod.core.patterns.grid import Pattern
from trackmod.spec.grid import EMPTY
from trackmod.trackers.s3m.spec.cells import (
    EFFECT_BYTES,
    KEY_BYTES,
    MARKER_BYTE,
    ROW_TERMINATOR_BYTE,
    VOLUME_BYTE,
)
from trackmod.trackers.s3m.spec.sizes import PATTERN_LENGTH_BYTES


def packed_bytes(pattern: Pattern) -> int:
    """How many bytes a pattern's packed cell stream occupies, without building it.

    Nothing here is remembered between cells, so what a pattern costs is a count of the groups its
    columns fill: a marker for every cell that states anything, two bytes wherever a key or a sample is
    stated, one for a volume, two for an effect, and one closing byte a row. Silence therefore costs
    exactly one byte a row, which is the whole of what an empty pattern comes to.
    """
    keyed = (pattern.note != EMPTY) | (pattern.instrument != EMPTY)
    volumed = pattern.volume != EMPTY
    affected = pattern.effect != EMPTY
    return (
        ROW_TERMINATOR_BYTE * pattern.rows
        + MARKER_BYTE * int(np.count_nonzero(keyed | volumed | affected))
        + KEY_BYTES * int(np.count_nonzero(keyed))
        + VOLUME_BYTE * int(np.count_nonzero(volumed))
        + EFFECT_BYTES * int(np.count_nonzero(affected))
    )


def block_bytes(pattern: Pattern) -> int:
    """How many bytes a pattern's whole block occupies, the length it opens with counted in."""
    return PATTERN_LENGTH_BYTES + packed_bytes(pattern)

from trackmod.core.patterns.grid import Pattern
from trackmod.trackers.amiga.spec.cells import CELL_BYTES


def packed_bytes(pattern: Pattern) -> int:
    """How many bytes a pattern's stored cells occupy, without building them.

    Nothing here is packed: every position of the grid is written as four bytes whether it states
    anything or not, so a pattern costs the same whatever it holds and the answer is a product.
    """
    return CELL_BYTES * pattern.rows * pattern.channels

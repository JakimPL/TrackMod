from typing import Final

from trackmod.core.patterns.grid import Pattern
from trackmod.spec.width import BYTE_MAX
from trackmod.trackers.it.spec.cells import (
    CHANNEL_BYTE,
    CHANNEL_MARKER,
    MASK_BYTE,
    NO_COLUMNS,
)

WIDTH_ROW: Final = 0
WIDTH_MARKER_BYTES: Final = CHANNEL_BYTE + MASK_BYTE


def states_width(pattern: Pattern) -> bool:
    """Whether the stream spends a cell on naming the pattern's widest channel.

    A row lists the channels that carry something, so the stream reaches as far as the content does and a
    pattern whose widest channel holds silence comes back narrower than it was built. A pattern playing
    something there states its width by playing it; one that stays silent there needs the cell.
    """
    return not pattern.occupied[:, pattern.channels - 1].any()


def width_marker(pattern: Pattern) -> bytes:
    """The cell that names the widest channel, which a pattern reaching it with content already states.

    The cell announces that channel with a mask over no columns — two bytes that decode as the silence
    already sitting there — so the width survives a round trip while a reader sizing a pattern to the
    columns it carries reads the same grid it read before.
    """
    if not states_width(pattern):
        return b""

    return bytes([(pattern.channels | CHANNEL_MARKER) & BYTE_MAX, NO_COLUMNS])

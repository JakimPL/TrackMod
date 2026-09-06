from typing import Final

from trackmod.trackers.s3m.spec.flags import (
    CHANNEL_MUTED,
    CHANNEL_RIGHT,
    CHANNEL_SIDE_WIDTH,
    CHANNEL_UNUSED,
)
from trackmod.trackers.s3m.spec.sizes import CHANNELS_STORED

SIDES: Final = 2


def placed(channel: int) -> int:
    """The mixer slot one channel takes, alternating sides so a song opens spread across the field.

    Scream Tracker 3 numbers eight slots on the left and eight on the right, and lays a module's
    channels down one to each side in turn, which is the arrangement every module of this format opens
    with before any panning is stated.
    """
    pair, side = divmod(channel, SIDES)
    return side * CHANNEL_RIGHT + pair % CHANNEL_SIDE_WIDTH


def channel_table(channels: int) -> tuple[int, ...]:
    """The settings table a song of one width states: a mixer slot per channel, the rest left unused."""
    return tuple(placed(channel) if channel < channels else CHANNEL_UNUSED for channel in range(CHANNELS_STORED))


def stated_width(settings: tuple[int, ...]) -> int:
    """How many channels a settings table declares, which is the last slot it names and every one under it.

    A packed cell names its channel by the slot it takes in this table, so a table that leaves a gap in
    the middle still states every channel up to the last one it names.
    """
    return max((channel + 1 for channel, entry in enumerate(settings) if entry != CHANNEL_UNUSED), default=0)


def sounded(entry: int) -> bool:
    """Whether a channel's settings leave it playing, as against muted or left out of the module."""
    return entry != CHANNEL_UNUSED and not entry & CHANNEL_MUTED

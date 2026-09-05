from dataclasses import dataclass

from trackmod.trackers.it.spec.cells import NO_COLUMNS, UNSET


@dataclass
class ChannelMemory:
    """What a channel remembers between its present rows, which the reuse mask bits refer to.

    A channel starts out remembering a mask over no columns, so a row naming a channel before any mask
    has been stated reads as the silence already sitting there.
    """

    note: int = UNSET
    instrument: int = UNSET
    volume: int = UNSET
    command: int = UNSET
    parameter: int = UNSET
    mask: int = NO_COLUMNS

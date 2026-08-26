from collections.abc import Mapping
from enum import StrEnum, unique
from typing import Final

from trackmod.trackers.it.spec.identity import TRACKER_BITS, VERSION_MASK


@unique
class Tracker(StrEnum):
    """A program that writes this format, as a file's created-with field names one.

    Impulse Tracker left fields spare and the programs that came after it spend them, so which program
    wrote a file is what says which conventions to read it under.
    """

    IMPULSE_TRACKER = "impulse_tracker"
    SCHISM_TRACKER = "schism_tracker"
    OPEN_MPT = "openmpt"


TRACKER_NUMBERS: Final[Mapping[int, Tracker]] = {
    0x0: Tracker.IMPULSE_TRACKER,
    0x1: Tracker.SCHISM_TRACKER,
    0x5: Tracker.OPEN_MPT,
}


def wrote(created_with: int) -> Tracker | None:
    """The program a created-with field names, where it names one this library reads.

    Each program took a number of its own to sit above the version it states, so the number is what a
    reader goes by. A field carrying a number no program here claims leaves the writer unnamed.
    """
    return TRACKER_NUMBERS.get(created_with >> TRACKER_BITS)


def version(created_with: int) -> int:
    """The version a created-with field states, below the number naming the program that wrote it.

    Each program spells those bits its own way, so they are answered as the field holds them and the
    program named beside them is what says how to read them.
    """
    return created_with & VERSION_MASK

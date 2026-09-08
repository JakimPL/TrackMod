from collections.abc import Mapping
from enum import StrEnum, unique
from typing import Final

from trackmod.binary.text import decode_name
from trackmod.module.provenance import Evidence, Provenance
from trackmod.spec.application import APPLICATION_NAME, APPLICATION_TAG
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
    CHIBI_TRACKER = "chibi_tracker"
    TRACKMOD = "trackmod"

    @property
    def label(self) -> str:
        """The program's name as it is written for a reader."""
        return LABELS[self]


LABELS: Final[Mapping[Tracker, str]] = {
    Tracker.IMPULSE_TRACKER: "Impulse Tracker",
    Tracker.SCHISM_TRACKER: "Schism Tracker",
    Tracker.OPEN_MPT: "OpenMPT",
    Tracker.CHIBI_TRACKER: "ChibiTracker",
    Tracker.TRACKMOD: APPLICATION_NAME,
}

TRACKER_NUMBERS: Final[Mapping[int, Tracker]] = {
    0x0: Tracker.IMPULSE_TRACKER,
    0x1: Tracker.SCHISM_TRACKER,
    0x5: Tracker.OPEN_MPT,
}

TRACKER_SIGNATURES: Final[Mapping[bytes, Tracker]] = {
    b"OMPT": Tracker.OPEN_MPT,
    b"CHBI": Tracker.CHIBI_TRACKER,
    APPLICATION_TAG: Tracker.TRACKMOD,
}


def wrote(created_with: int) -> Tracker | None:
    """The program a created-with field names, where it names one this library reads.

    Each program took a number of its own to sit above the version it states, so the number is what a
    reader goes by. A field carrying a number no program here claims leaves the writer unnamed.
    """
    return TRACKER_NUMBERS.get(created_with >> TRACKER_BITS)


def signed(signature: bytes) -> Tracker | None:
    """The program a signature names, where it names one this library reads.

    The four bytes this format reserves are where several trackers write a mark of their own, so a file
    carrying one names its writer more closely than the number above its version does: the number states
    the reading a file was written for, and a program keeping the reading it inherited states it too.
    """
    return TRACKER_SIGNATURES.get(signature)


def version(created_with: int) -> int:
    """The version a created-with field states, below the number naming the program that wrote it.

    Each program spells those bits its own way, so they are answered as the field holds them and the
    program named beside them is what says how to read them.
    """
    return created_with & VERSION_MASK


def stated_provenance(*, created_with: int, signature: bytes) -> Provenance:
    """What a header states about the program that wrote it.

    A file signing the bytes this format reserves names its writer outright, so that is the answer where
    it is there. Behind it stands the number above the version, which every file states and which names
    the reading the file was written for.
    """
    marked = signed(signature)
    if marked is not None:
        return Provenance(
            evidence=Evidence.SIGNED,
            stated=decode_name(signature),
            tracker=marked.label,
        )

    numbered = wrote(created_with)
    return Provenance(
        evidence=Evidence.NUMBERED,
        stated=f"0x{created_with:04X}",
        tracker=numbered.label if numbered else None,
    )

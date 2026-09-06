from collections.abc import Mapping
from typing import Final

from trackmod.trackers.mod.spec.ranges import CANONICAL_CHANNELS

DEFAULT_TAG: Final = b"M.K."
WIDE_TAG: Final = b"M!K!"

MULTICHANNEL: Final = "multichannel"
SINGLE_DIGIT_CHANNELS: Final = 9

NAMED_TAGS: Final[tuple[tuple[bytes, int, str], ...]] = (
    (DEFAULT_TAG, CANONICAL_CHANNELS, "Amiga ProTracker"),
    (WIDE_TAG, CANONICAL_CHANNELS, "Amiga ProTracker"),
    (b"M&K!", CANONICAL_CHANNELS, "His Master's Noise"),
    (b"N.T.", CANONICAL_CHANNELS, "NoiseTracker"),
    (b".M.K", CANONICAL_CHANNELS, "NoiseTracker"),
    (b"LARD", CANONICAL_CHANNELS, "Amiga ProTracker"),
    (b"NSMS", CANONICAL_CHANNELS, "Amiga ProTracker"),
    (b"FLT4", CANONICAL_CHANNELS, "StarTrekker"),
    (b"CD61", 6, "Octalyser"),
    (b"CD81", 8, "Octalyser"),
    (b"FA04", 4, "Digital Tracker"),
    (b"FA06", 6, "Digital Tracker"),
    (b"FA08", 8, "Digital Tracker"),
    (b"TDZ1", 1, "TakeTracker"),
    (b"TDZ2", 2, "TakeTracker"),
    (b"TDZ3", 3, "TakeTracker"),
    (b"TDZ4", 4, "TakeTracker"),
)

SPLIT_TAGS: Final[Mapping[bytes, str]] = {
    b"FLT8": "stores each eight-channel pattern as two four-channel ones",
}

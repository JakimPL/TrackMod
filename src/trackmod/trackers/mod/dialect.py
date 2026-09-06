from collections.abc import Mapping
from typing import Final

from pydantic import BaseModel
from pydantic import Field as ModelField

from trackmod.schema.config import FROZEN
from trackmod.trackers.mod.spec.identity import TAG_BYTES
from trackmod.trackers.mod.spec.ranges import (
    CANONICAL_CHANNELS,
    EXTENDED_MIN_CHANNELS,
    STRUCTURAL_MAX_CHANNELS,
)

SINGLE_DIGIT_CHANNELS: Final = 9


class Dialect(BaseModel):
    """One four-byte tag a module carries at the end of its header, and what the tag settles.

    Amiga ProTracker wrote no version anywhere; the tag is what a reader has, and every tracker that
    widened the format past four channels wrote its own. The tag therefore decides the channel count
    before a single pattern byte is read, which is what makes a file whose length disagrees with its
    tag still parse the way a player reads it.
    """

    model_config = FROZEN

    tag: bytes = ModelField(min_length=TAG_BYTES, max_length=TAG_BYTES)
    channels: int = ModelField(ge=EXTENDED_MIN_CHANNELS, le=STRUCTURAL_MAX_CHANNELS)
    tracker: str = ModelField(min_length=1)


def channel_tag(channels: int) -> bytes:
    """The tag the multichannel families spell ``channels`` with, a digit to a character.

    Four characters hold two digits and the letters that name them, so the families reach ninety-nine
    channels and the grammar stops there.
    """
    if channels <= SINGLE_DIGIT_CHANNELS:
        return b"%dCHN" % channels

    return b"%dCH" % channels


NAMED: Final = (
    Dialect(tag=b"M.K.", channels=CANONICAL_CHANNELS, tracker="Amiga ProTracker"),
    Dialect(tag=b"M!K!", channels=CANONICAL_CHANNELS, tracker="Amiga ProTracker"),
    Dialect(tag=b"M&K!", channels=CANONICAL_CHANNELS, tracker="His Master's Noise"),
    Dialect(tag=b"N.T.", channels=CANONICAL_CHANNELS, tracker="NoiseTracker"),
    Dialect(tag=b".M.K", channels=CANONICAL_CHANNELS, tracker="NoiseTracker"),
    Dialect(tag=b"LARD", channels=CANONICAL_CHANNELS, tracker="Amiga ProTracker"),
    Dialect(tag=b"NSMS", channels=CANONICAL_CHANNELS, tracker="Amiga ProTracker"),
    Dialect(tag=b"FLT4", channels=CANONICAL_CHANNELS, tracker="StarTrekker"),
    Dialect(tag=b"CD61", channels=6, tracker="Octalyser"),
    Dialect(tag=b"CD81", channels=8, tracker="Octalyser"),
    Dialect(tag=b"FA04", channels=4, tracker="Digital Tracker"),
    Dialect(tag=b"FA06", channels=6, tracker="Digital Tracker"),
    Dialect(tag=b"FA08", channels=8, tracker="Digital Tracker"),
    Dialect(tag=b"TDZ1", channels=1, tracker="TakeTracker"),
    Dialect(tag=b"TDZ2", channels=2, tracker="TakeTracker"),
    Dialect(tag=b"TDZ3", channels=3, tracker="TakeTracker"),
    Dialect(tag=b"TDZ4", channels=4, tracker="TakeTracker"),
)

GENERATED: Final = tuple(
    Dialect(tag=channel_tag(channels), channels=channels, tracker="multichannel")
    for channels in range(EXTENDED_MIN_CHANNELS, STRUCTURAL_MAX_CHANNELS + 1)
)

DIALECTS: Final[Mapping[bytes, Dialect]] = {dialect.tag: dialect for dialect in (*GENERATED, *NAMED)}

DEFAULT_DIALECT: Final = DIALECTS[b"M.K."]
WIDE_DIALECT: Final = DIALECTS[b"M!K!"]

SPLIT_PATTERNS: Final[Mapping[bytes, str]] = {
    b"FLT8": "stores each eight-channel pattern as two four-channel ones",
}

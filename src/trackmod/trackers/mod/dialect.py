from collections.abc import Mapping
from typing import Final

from pydantic import BaseModel
from pydantic import Field as ModelField

from trackmod.schema.config import FROZEN
from trackmod.trackers.mod.spec.dialects import (
    DEFAULT_TAG,
    MULTICHANNEL,
    NAMED_TAGS,
    SINGLE_DIGIT_CHANNELS,
    WIDE_TAG,
)
from trackmod.trackers.mod.spec.identity import TAG_BYTES
from trackmod.trackers.mod.spec.ranges import EXTENDED_MIN_CHANNELS, STRUCTURAL_MAX_CHANNELS


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


NAMED: Final = tuple(Dialect(tag=tag, channels=channels, tracker=tracker) for tag, channels, tracker in NAMED_TAGS)

GENERATED: Final = tuple(
    Dialect(tag=channel_tag(channels), channels=channels, tracker=MULTICHANNEL)
    for channels in range(EXTENDED_MIN_CHANNELS, STRUCTURAL_MAX_CHANNELS + 1)
)

DIALECTS: Final[Mapping[bytes, Dialect]] = {dialect.tag: dialect for dialect in (*GENERATED, *NAMED)}

DEFAULT_DIALECT: Final = DIALECTS[DEFAULT_TAG]
WIDE_DIALECT: Final = DIALECTS[WIDE_TAG]

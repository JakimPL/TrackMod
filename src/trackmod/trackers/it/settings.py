from typing import Annotated

from pydantic import BaseModel, Field

from trackmod.schema.config import FROZEN
from trackmod.spec.width import BYTE_MAX
from trackmod.trackers.it.spec.defaults import (
    DEFAULT_CHANNEL_PANNING,
    DEFAULT_CHANNEL_VOLUME,
    DEFAULT_FLAGS,
    DEFAULT_GLOBAL_VOLUME,
    DEFAULT_MESSAGE,
    DEFAULT_MIX_VOLUME,
    DEFAULT_PANNING_SEPARATION,
)
from trackmod.trackers.it.spec.flags import HeaderFlag
from trackmod.trackers.it.spec.identity import CREATED_WITH
from trackmod.trackers.it.spec.sizes import CHANNELS_STORED

ChannelBytes = Annotated[
    tuple[Annotated[int, Field(ge=0, le=BYTE_MAX)], ...],
    Field(min_length=CHANNELS_STORED, max_length=CHANNELS_STORED),
]


class ITSettings(BaseModel):
    """The song-wide values this format carries that the shared model leaves to each format.

    The channel tables are as wide as the header stores them, which is the format's own channel count
    rather than the song's — a module with more channels than that leaves the extra ones at the defaults
    the tracker applies.

    ``message`` is the free text the format attaches to a module, which a tracker shows beside the piece
    and a producer is free to spend on whatever it wants a file to carry with it.

    ``created_with`` is the version field naming the program that wrote a file
    (:func:`~trackmod.trackers.it.version.wrote`). A file read here keeps the one it arrived with, so a
    module written back states the same origin it stated before, and a song built from nothing states
    the version this format's own tracker wrote.
    """

    model_config = FROZEN

    global_volume: int = DEFAULT_GLOBAL_VOLUME
    mix_volume: int = DEFAULT_MIX_VOLUME
    panning_separation: int = DEFAULT_PANNING_SEPARATION
    channel_panning: ChannelBytes = DEFAULT_CHANNEL_PANNING
    channel_volume: ChannelBytes = DEFAULT_CHANNEL_VOLUME
    flags: HeaderFlag = DEFAULT_FLAGS
    message: str = DEFAULT_MESSAGE
    created_with: int = CREATED_WITH

from typing import Annotated

from pydantic import BaseModel, Field

from trackmod.schema.config import FROZEN
from trackmod.spec.width import BYTE_MAX, WORD_MAX
from trackmod.trackers.it.extensions import Extensions
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

PanningSeparation = Annotated[int, Field(ge=0, le=BYTE_MAX)]
Version = Annotated[int, Field(ge=0, le=WORD_MAX)]


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

    ``extensions`` holds what a writer appended past the records Impulse Tracker itself laid out, so a
    file carrying channel names, an editing history or the properties a later tracker keeps for itself
    reads with all of them and writes them back (:class:`~trackmod.trackers.it.extensions.Extensions`).
    """

    model_config = FROZEN

    global_volume: int = DEFAULT_GLOBAL_VOLUME
    mix_volume: int = DEFAULT_MIX_VOLUME
    panning_separation: PanningSeparation = DEFAULT_PANNING_SEPARATION
    channel_panning: ChannelBytes = DEFAULT_CHANNEL_PANNING
    channel_volume: ChannelBytes = DEFAULT_CHANNEL_VOLUME
    flags: HeaderFlag = DEFAULT_FLAGS
    message: str = DEFAULT_MESSAGE
    created_with: Version = CREATED_WITH
    extensions: Extensions = Extensions()

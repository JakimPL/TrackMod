from typing import Annotated

from pydantic import BaseModel, Field

from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Panning
from trackmod.spec.width import BYTE_MAX
from trackmod.trackers.s3m.spec.defaults import (
    DEFAULT_FLAGS,
    DEFAULT_GLOBAL_VOLUME,
    DEFAULT_MIX_VOLUME,
    DEFAULT_STEREO,
)
from trackmod.trackers.s3m.spec.flags import HeaderFlag
from trackmod.trackers.s3m.spec.identity import CREATED_WITH
from trackmod.trackers.s3m.spec.sizes import CHANNELS_STORED

ChannelBytes = Annotated[
    tuple[Annotated[int, Field(ge=0, le=BYTE_MAX)], ...],
    Field(min_length=CHANNELS_STORED, max_length=CHANNELS_STORED),
]

ChannelPanning = Annotated[
    tuple[Panning | None, ...],
    Field(min_length=CHANNELS_STORED, max_length=CHANNELS_STORED),
]


class S3MSettings(BaseModel):
    """The song-wide values this format carries that the shared model leaves to each format.

    ``channels`` is the settings table the header states a module's width in: a mixer slot for each
    channel the song plays and an unused marker for the rest. A file read back carries the table it
    held, so a module written again places its channels where they stood; a song built from nothing
    leaves it unstated and the writer lays the channels out the way every module of this format opens.

    ``channel_panning`` is where each channel opens on the shared 0..255 stereo field, one entry to
    each of the slots the header's own panning block holds, and ``None`` for a channel claiming no
    position of its own. A file attaching no such block leaves the whole table unstated, and every
    channel opens on the side its mixer slot puts it.

    ``stereo`` is the switch the mixing-volume byte reserves its top bit for, and ``mix_volume`` the
    level in the seven bits below it.

    ``created_with`` is the version field naming the program that wrote a file, so a module written back
    states the same origin it stated before.
    """

    model_config = FROZEN

    global_volume: int = DEFAULT_GLOBAL_VOLUME
    mix_volume: int = DEFAULT_MIX_VOLUME
    stereo: bool = DEFAULT_STEREO
    flags: HeaderFlag = DEFAULT_FLAGS
    channels: ChannelBytes | None = None
    channel_panning: ChannelPanning | None = None
    created_with: int = CREATED_WITH

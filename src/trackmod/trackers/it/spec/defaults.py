from typing import Final

from trackmod.trackers.it.spec.flags import HeaderFlag, SamplePanning
from trackmod.trackers.it.spec.ranges import (
    CHANNEL_VOLUME_FULL,
    MAX_GLOBAL_VOLUME,
    PAN_CENTER,
)
from trackmod.trackers.it.spec.sizes import CHANNELS_STORED

DEFAULT_GLOBAL_VOLUME: Final = MAX_GLOBAL_VOLUME
DEFAULT_MIX_VOLUME: Final = 48
DEFAULT_PANNING_SEPARATION: Final = 128

DEFAULT_CHANNEL_PANNING: Final = (PAN_CENTER,) * CHANNELS_STORED
DEFAULT_CHANNEL_VOLUME: Final = (CHANNEL_VOLUME_FULL,) * CHANNELS_STORED
DEFAULT_FLAGS: Final = HeaderFlag.USE_INSTRUMENTS | HeaderFlag.LINEAR_SLIDES
DEFAULT_MESSAGE: Final = ""

C5_NOTE: Final = 60
NO_SAMPLE: Final = 0
PANNING_DISABLED: Final = SamplePanning.ENABLED | PAN_CENTER

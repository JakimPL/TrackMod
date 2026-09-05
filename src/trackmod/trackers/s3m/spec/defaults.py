from typing import Final

from trackmod.trackers.s3m.spec.flags import HeaderFlag
from trackmod.trackers.s3m.spec.ranges import MAX_GLOBAL_VOLUME

DEFAULT_SPEED: Final = 6
DEFAULT_TEMPO: Final = 125

DEFAULT_GLOBAL_VOLUME: Final = MAX_GLOBAL_VOLUME
DEFAULT_MIX_VOLUME: Final = 48
DEFAULT_STEREO: Final = True
DEFAULT_FLAGS: Final = HeaderFlag(0)

NO_LOOP: Final = 0
NO_FRAMES: Final = 0

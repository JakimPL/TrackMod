from typing import Final

from trackmod.spec.application import APPLICATION_SIGNATURE
from trackmod.trackers.xm.spec.flags import HeaderFlag
from trackmod.trackers.xm.spec.ranges import PAN_CENTER

DEFAULT_TRACKER: Final = APPLICATION_SIGNATURE
DEFAULT_FLAGS: Final = HeaderFlag.LINEAR_FREQUENCY
DEFAULT_PANNING: Final = PAN_CENTER
DEFAULT_SPEED: Final = 6

INSTRUMENT_TYPE: Final = 0
PACKING_TYPE: Final = 0

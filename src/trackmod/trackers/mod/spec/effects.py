from typing import Final

from trackmod.limits.bound import Bound
from trackmod.spec.levels import MAX_PANNING
from trackmod.spec.width import BYTE_MAX, NIBBLE_MAX
from trackmod.trackers.amiga.spec.ranges import MAX_BREAK_ROW
from trackmod.trackers.mod.spec.ranges import (
    MAX_EFFECT_SPEED,
    MAX_EFFECT_TEMPO,
    MIN_EFFECT_SPEED,
    MIN_EFFECT_TEMPO,
)

SPEED_PARAMETER: Final = Bound(minimum=MIN_EFFECT_SPEED, maximum=MAX_EFFECT_SPEED)
TEMPO_PARAMETER: Final = Bound(minimum=MIN_EFFECT_TEMPO, maximum=MAX_EFFECT_TEMPO)
ORDER_PARAMETER: Final = Bound(minimum=0, maximum=BYTE_MAX)
ROW_PARAMETER: Final = Bound(minimum=0, maximum=MAX_BREAK_ROW)
NIBBLE_PARAMETER: Final = Bound(minimum=0, maximum=NIBBLE_MAX)
PANNING_PARAMETER: Final = Bound(minimum=0, maximum=MAX_PANNING)

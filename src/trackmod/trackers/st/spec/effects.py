from typing import Final

from trackmod.limits.bound import Bound
from trackmod.spec.width import BYTE_MAX
from trackmod.trackers.amiga.spec.ranges import MAX_BREAK_ROW
from trackmod.trackers.st.spec.ranges import MAX_EFFECT_SPEED, MIN_EFFECT_SPEED

SPEED_PARAMETER: Final = Bound(minimum=MIN_EFFECT_SPEED, maximum=MAX_EFFECT_SPEED)
ORDER_PARAMETER: Final = Bound(minimum=0, maximum=BYTE_MAX)
ROW_PARAMETER: Final = Bound(minimum=0, maximum=MAX_BREAK_ROW)

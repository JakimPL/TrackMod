from typing import Final

from trackmod.core.timing.timings import Timings
from trackmod.trackers.mod.spec.effects import SPEED_PARAMETER, TEMPO_PARAMETER

TIMINGS: Final = Timings(speed=SPEED_PARAMETER, tempo=TEMPO_PARAMETER)

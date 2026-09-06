from typing import Final

from trackmod.core.timing.timings import Timings
from trackmod.limits.capability import Capability
from trackmod.trackers.st.spec.capacities import CAPACITIES

TIMINGS: Final = Timings(
    speed=CAPACITIES[Capability.SPEED].structural,
    tempo=CAPACITIES[Capability.TEMPO].structural,
)

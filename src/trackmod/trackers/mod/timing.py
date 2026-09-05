from typing import Final

from trackmod.core.timing.lattice import exact_timings as shared_exact_timings
from trackmod.core.timing.lattice import nearest_timing as shared_nearest_timing
from trackmod.core.timing.lattice import row_frames as shared_row_frames
from trackmod.core.timing.timing import Timing
from trackmod.trackers.mod.spec.effects import SPEED_PARAMETER, TEMPO_PARAMETER

SPEED_BOUND: Final = SPEED_PARAMETER
TEMPO_BOUND: Final = TEMPO_PARAMETER


def row_frames(speed: int, tempo: int, *, frame_rate: int) -> int:
    """The frames one Amiga ProTracker row spans, bound to the clock its own effect reaches.

    The header carries no clock at all: a module starts at the one every tracker of this lineage starts
    at, and a song reaches another by setting it in a cell. The ranges here are therefore the effect's,
    which is the only place this format states a speed or a tempo.
    """
    return shared_row_frames(
        speed,
        tempo,
        frame_rate=frame_rate,
        speed_bound=SPEED_BOUND,
        tempo_bound=TEMPO_BOUND,
    )


def exact_timings(*, frame_rate: int, speed: int) -> list[Timing]:
    """Every Amiga ProTracker tempo whose row is a whole number of frames at one speed."""
    return shared_exact_timings(
        frame_rate=frame_rate,
        speed=speed,
        speed_bound=SPEED_BOUND,
        tempo_bound=TEMPO_BOUND,
    )


def nearest_timing(target_frames: int, *, frame_rate: int, speed: int) -> Timing:
    """The Amiga ProTracker timing whose row length is closest to a target."""
    return shared_nearest_timing(
        target_frames,
        frame_rate=frame_rate,
        speed=speed,
        speed_bound=SPEED_BOUND,
        tempo_bound=TEMPO_BOUND,
    )

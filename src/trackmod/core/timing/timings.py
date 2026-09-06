from pydantic import BaseModel

from trackmod.core.timing.lattice import exact_timings, nearest_timing, row_frames
from trackmod.core.timing.timing import Timing
from trackmod.limits.bound import Bound
from trackmod.schema.config import FROZEN


class Timings(BaseModel):
    """The speed and tempo ranges one format's clock runs inside, which is the whole of what its lattice needs.

    A row's length follows from the two numbers alone, so a format states its two ranges here and asks
    the shared lattice its questions through them. Where each range comes from is the format's own
    business: three of them read it off the capacity table, and the one whose header states no clock at
    all reads it off the effect that sets one.
    """

    model_config = FROZEN

    speed: Bound
    tempo: Bound

    def row_frames(self, speed: int, tempo: int, *, frame_rate: int) -> int:
        """The frames one row spans, bound to this format's speed and tempo ranges."""
        return row_frames(speed, tempo, frame_rate=frame_rate, speed_bound=self.speed, tempo_bound=self.tempo)

    def exact_timings(self, *, frame_rate: int, speed: int) -> list[Timing]:
        """Every tempo of this format whose row is a whole number of frames at one speed."""
        return exact_timings(frame_rate=frame_rate, speed=speed, speed_bound=self.speed, tempo_bound=self.tempo)

    def nearest_timing(self, target_frames: int, *, frame_rate: int, speed: int) -> Timing:
        """The timing of this format whose row length is closest to a target."""
        return nearest_timing(
            target_frames,
            frame_rate=frame_rate,
            speed=speed,
            speed_bound=self.speed,
            tempo_bound=self.tempo,
        )

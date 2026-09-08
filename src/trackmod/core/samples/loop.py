from __future__ import annotations

from enum import StrEnum, unique

from pydantic import BaseModel, model_validator

from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Frames


@unique
class LoopMode(StrEnum):
    """How playback repeats a looped region.

    ``FORWARD`` plays the region from ``begin`` each time round. ``PING_PONG`` alternates direction,
    playing it forward and then backward. Only Impulse Tracker and FastTracker 2 store ping-pong loops.
    """

    FORWARD = "forward"
    PING_PONG = "ping_pong"


class Loop(BaseModel):
    """A half-open frame range ``[begin, end)`` that playback repeats on reaching ``end``.

    Args:
        begin: The first frame of the repeated region.
        end: One frame past the last, so the region spans ``end - begin`` frames.
        mode: Whether the region plays forward each time, or alternates direction.

    Raises:
        ValidationError: when ``end`` is not above ``begin``. A loop spans at least one frame.

    Example:
        >>> from trackmod import Loop
        >>> Loop(begin=8, end=64).frames
        56
        >>> Loop(begin=8, end=64).mode
        <LoopMode.FORWARD: 'forward'>
    """

    model_config = FROZEN

    begin: Frames
    end: Frames
    mode: LoopMode = LoopMode.FORWARD

    @model_validator(mode="after")
    def _inhabited(self) -> Loop:
        if self.end <= self.begin:
            raise ValueError(f"loop {self.begin}..{self.end} must span at least one frame")

        return self

    @property
    def frames(self) -> int:
        """How many frames the repeated region spans."""
        return self.end - self.begin

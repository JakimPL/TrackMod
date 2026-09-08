from __future__ import annotations

from enum import StrEnum, unique

from pydantic import BaseModel, model_validator

from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Frames


@unique
class LoopMode(StrEnum):
    """How playback repeats a looped region."""

    FORWARD = "forward"
    PING_PONG = "ping_pong"


class Loop(BaseModel):
    """A half-open frame range ``[begin, end)`` playback repeats once it reaches ``end``.

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

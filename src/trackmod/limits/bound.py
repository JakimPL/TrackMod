from __future__ import annotations

from pydantic import BaseModel, model_validator

from trackmod.schema.config import FROZEN


class Bound(BaseModel):
    """An inclusive integer range a value must land in."""

    model_config = FROZEN

    minimum: int
    maximum: int

    @model_validator(mode="after")
    def _inhabited(self) -> Bound:
        if self.minimum > self.maximum:
            raise ValueError(f"bound {self.minimum}..{self.maximum} is empty")

        return self

    def contains(self, value: int) -> bool:
        """Whether ``value`` lies within the range."""
        return self.minimum <= value <= self.maximum

    def clamp(self, value: int) -> int:
        """``value`` moved to the nearer end of the range whenever it lies outside.

        This is for a caller writing a quantity a format has to hold whatever was asked for -- an
        envelope node on its value grid, say -- where the nearest storable value is the answer and a
        violation would leave nothing to write.
        """
        return min(self.maximum, max(self.minimum, value))

    @property
    def room(self) -> int:
        """How many distinct values the range holds."""
        return self.maximum - self.minimum + 1

    def __str__(self) -> str:
        return f"{self.minimum}..{self.maximum}"

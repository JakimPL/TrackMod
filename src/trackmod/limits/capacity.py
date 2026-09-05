from __future__ import annotations

from pydantic import BaseModel, model_validator

from trackmod.limits.bound import Bound
from trackmod.schema.config import FROZEN


class Capacity(BaseModel):
    """The three ceilings one format states for one quantity, from the tightest to the widest.

    ``canonical`` is what the tracker the format names honoured in its own editor, ``extended`` what the
    players descended from it read, and ``structural`` what the record layout physically holds. Each
    contains the one before it, so a value passing a wider bound has already passed the tighter ones and
    the level it breaks is the one worth reporting.

    A field with no headroom at all states the same bound three times, which is what
    :meth:`fixed` is for.
    """

    model_config = FROZEN

    canonical: Bound
    extended: Bound
    structural: Bound

    @model_validator(mode="after")
    def _nested(self) -> Capacity:
        for tighter, wider, names in (
            (self.canonical, self.extended, ("canonical", "extended")),
            (self.extended, self.structural, ("extended", "structural")),
        ):
            if not wider.contains(tighter.minimum) or not wider.contains(tighter.maximum):
                raise ValueError(f"{names[0]} bound {tighter} escapes the {names[1]} bound {wider}")

        return self

    @classmethod
    def fixed(cls, bound: Bound) -> Capacity:
        """A capacity whose three bounds coincide, for a field with no headroom at any level."""
        return cls(canonical=bound, extended=bound, structural=bound)

from collections.abc import Mapping
from types import MappingProxyType

from pydantic import BaseModel, field_validator

from trackmod.limits.bound import Bound
from trackmod.limits.capability import Capability
from trackmod.limits.capacity import Capacity
from trackmod.limits.compliance import Compliance
from trackmod.limits.reach import width
from trackmod.limits.tier import Tier
from trackmod.limits.violation import Violation
from trackmod.schema.config import FROZEN


class Limits(BaseModel):
    """A format's capacity table read at one compliance level.

    :meth:`bound` answers what a caller may use; :meth:`check` grades a value it already has. A value is
    graded against the widest ceiling it passes, and reported when that ceiling is the one this table is
    read at or a wider one — so a value the layout cannot hold is reported at every level, a value the
    players descended from the tracker refuse is reported at the two tighter levels, and a value only the
    tracker's own editor refuses is reported at the tightest. That single rule is the whole mechanism: a
    module held to a wider level is not one that skips validation, it is one validated against a wider
    bound.
    """

    model_config = FROZEN

    compliance: Compliance
    capacities: Mapping[Capability, Capacity]

    @field_validator("capacities", mode="after")
    @classmethod
    def _sealed(cls, capacities: Mapping[Capability, Capacity]) -> Mapping[Capability, Capacity]:
        """Hand the table out as a read-only view, so a frozen model stays frozen all the way down."""
        return MappingProxyType(dict(capacities))

    def declares(self, capability: Capability) -> bool:
        """Whether this format states a capacity for ``capability`` at all.

        A format states a capacity for each quantity it keeps a field for, so this is what a caller
        grading a value it found in a song asks before grading it.
        """
        return capability in self.capacities

    def capacity(self, capability: Capability) -> Capacity:
        """The declared capacity for ``capability``.

        Raises:
            ValueError: when the format keeps no field for ``capability`` and so states no capacity.
        """
        capacity = self.capacities.get(capability)
        if capacity is None:
            raise ValueError(f"this format keeps no field for {capability.value} and states no capacity for it")

        return capacity

    def bound(self, capability: Capability) -> Bound:
        """The effective bound at this compliance level."""
        capacity = self.capacity(capability)
        match self.compliance:
            case Compliance.CANONICAL:
                return capacity.canonical
            case Compliance.EXTENDED:
                return capacity.extended
            case Compliance.STRUCTURAL:
                return capacity.structural

    def tiers(self, capability: Capability) -> tuple[Tier, ...]:
        """The three ceilings a capability states, widest first, each with the level passing it breaks."""
        capacity = self.capacity(capability)
        return (
            Tier(level=Compliance.STRUCTURAL, bound=capacity.structural),
            Tier(level=Compliance.EXTENDED, bound=capacity.extended),
            Tier(level=Compliance.CANONICAL, bound=capacity.canonical),
        )

    def check(self, capability: Capability, value: int, *, subject: str) -> Violation | None:
        """Grade ``value`` against ``capability``, returning the violation it commits, if any.

        The widest ceiling the value passes is the one it is graded against, because a value outside a
        wide bound is outside every tighter one and the widest says who will still read it back.
        """
        for tier in self.tiers(capability):
            if tier.bound.contains(value):
                continue

            if width(tier.level) < width(self.compliance):
                return None

            return Violation(
                capability=capability,
                value=value,
                bound=tier.bound,
                level=tier.level,
                subject=subject,
            )

        return None

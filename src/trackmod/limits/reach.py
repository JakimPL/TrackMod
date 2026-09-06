from collections.abc import Sequence
from typing import Final

from trackmod.limits.compliance import Compliance
from trackmod.limits.violation import Violation

LEVELS: Final = (Compliance.CANONICAL, Compliance.EXTENDED, Compliance.STRUCTURAL)


def width(compliance: Compliance) -> int:
    """How wide a level is, counted from the tightest, so two levels can be compared."""
    return LEVELS.index(compliance)


def reached(violations: Sequence[Violation]) -> Compliance | None:
    """The strictest level a song fits inside, or ``None`` for a song that fits none of them.

    A song breaking nothing is canonical: it opens in the tracker its format names. A song breaking a
    canonical bound needs the level above, and so on up. A song breaking a structural bound carries
    values no record layout holds, so no level holds it and the structural violations say which.
    """
    broken = max((width(violation.level) for violation in violations), default=-1)
    if broken == width(Compliance.STRUCTURAL):
        return None

    return LEVELS[broken + 1]


def beyond(violations: Sequence[Violation], compliance: Compliance) -> tuple[Violation, ...]:
    """Every violation naming a bound at or past ``compliance``, which is what holding to it refuses."""
    return tuple(violation for violation in violations if width(violation.level) >= width(compliance))

from collections.abc import Sequence
from typing import Final

from trackmod.limits.compliance import Compliance
from trackmod.limits.violation import Violation

LEVELS: Final = (Compliance.CANONICAL, Compliance.EXTENDED, Compliance.STRUCTURAL)


def depth(compliance: Compliance) -> int:
    """How far a level sits from the tightest one, so two levels can be compared."""
    return LEVELS.index(compliance)


def reached(violations: Sequence[Violation]) -> Compliance | None:
    """The strictest level a song fits inside, or ``None`` for a song that fits none of them.

    A song breaking nothing is canonical: it opens in the tracker its format names. A song breaking a
    canonical bound needs the level above, and so on up. A song breaking a structural bound carries
    values no record layout holds, so no level holds it and the structural violations say which.
    """
    broken = max((depth(violation.level) for violation in violations), default=-1)
    if broken == depth(Compliance.STRUCTURAL):
        return None

    return LEVELS[broken + 1]


def beyond(violations: Sequence[Violation], compliance: Compliance) -> tuple[Violation, ...]:
    """Every violation naming a bound at or past ``compliance``, which is what holding to it refuses."""
    return tuple(violation for violation in violations if depth(violation.level) >= depth(compliance))

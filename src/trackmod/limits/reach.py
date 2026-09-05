from collections.abc import Mapping, Sequence
from typing import Final

from trackmod.limits.compliance import Compliance
from trackmod.limits.severity import Severity
from trackmod.limits.violation import Violation

LEVELS: Final = (Compliance.CANONICAL, Compliance.EXTENDED, Compliance.STRUCTURAL)

BREAKS: Final[Mapping[Severity, Compliance]] = {
    Severity.COMPLIANCE: Compliance.CANONICAL,
    Severity.EXTENDED: Compliance.EXTENDED,
    Severity.STRUCTURAL: Compliance.STRUCTURAL,
}


def depth(compliance: Compliance) -> int:
    """How far a level sits from the tightest one, so two levels can be compared."""
    return LEVELS.index(compliance)


def reached(violations: Sequence[Violation]) -> Compliance:
    """The strictest level a song fits inside, given every bound it passes at the strictest one.

    A song breaking nothing is canonical: it opens in the tracker its format names. A song breaking a
    canonical bound needs the level above, and so on up. A song breaking a structural bound reaches the
    widest level and fits none of them, which the structural violations it carries state.
    """
    broken = max((depth(BREAKS[violation.severity]) for violation in violations), default=-1)
    return LEVELS[min(broken + 1, len(LEVELS) - 1)]


def beyond(violations: Sequence[Violation], compliance: Compliance) -> tuple[Violation, ...]:
    """Every violation naming a bound at or past ``compliance``, which is what holding to it refuses."""
    return tuple(violation for violation in violations if depth(BREAKS[violation.severity]) >= depth(compliance))

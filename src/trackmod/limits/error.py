from collections.abc import Sequence

from trackmod.limits.violation import Violation


class LimitError(ValueError):
    """Raised when a module carries values a format refuses to store at its compliance level.

    ``violations`` holds every one of them, so you see all the problems at once instead of fixing them
    one at a time. The message is those violations joined by ``; ``.

    This subclasses ``ValueError``, so ``except ValueError`` catches it alongside the refusals a format
    raises for content it has no encoding for at all.

    Args:
        violations: The violations collected while checking the module.
    """

    def __init__(self, violations: Sequence[Violation]) -> None:
        self.violations = tuple(violations)
        super().__init__("; ".join(str(violation) for violation in self.violations))


def require(violations: Sequence[Violation]) -> None:
    """Raise :class:`LimitError` when any violation was collected.

    Raises:
        LimitError: when ``violations`` is non-empty.
    """
    if violations:
        raise LimitError(violations)

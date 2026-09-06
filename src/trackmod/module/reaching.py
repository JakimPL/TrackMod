from abc import ABC, abstractmethod

from trackmod.limits.compliance import Compliance
from trackmod.limits.error import require
from trackmod.limits.reach import beyond, reached
from trackmod.limits.violation import Violation


class Reaching(ABC):
    """How far a file's own values reach, which every binding answers from the bounds they pass.

    Reading holds a file to the widest level, because a file that exists is evidence its values were
    storable, so how far it reaches is a separate question from whether it is writable. Both answers
    follow from :meth:`exceeded` alone, which is what lets one statement of them serve every format.
    """

    @abstractmethod
    def exceeded(self) -> tuple[Violation, ...]:
        """Every bound the content passes at the strictest level, whatever level it is held to."""

    @property
    def reach(self) -> Compliance | None:
        """The strictest level the content fits inside, or ``None`` for content no level holds.

        Content whose values all sit inside a record layout reaches one of the three levels, and which
        one says who will read it back. Content carrying a value no layout holds reaches none of them,
        which :meth:`exceeded` states as a structural violation.
        """
        return reached(self.exceeded())

    def require_reach(self, compliance: Compliance) -> None:
        """Refuse content reaching past a level.

        Raises:
            LimitError: carrying every bound it passes at or beyond ``compliance``.
        """
        require(beyond(self.exceeded(), compliance))

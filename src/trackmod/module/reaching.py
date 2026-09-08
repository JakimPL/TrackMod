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
        """The strictest level the content fits inside.

        Content whose values all sit inside a record layout reaches one of the three levels, and which
        one says who will read it back.

        Returns:
            ``CANONICAL`` for content the format's own tracker accepts, ``EXTENDED`` for content
            needing a player descended from it, ``STRUCTURAL`` for content that can be stored but read
            faithfully by nothing, and ``None`` for content carrying a value no record layout holds.
        """
        return reached(self.exceeded())

    def require_reach(self, compliance: Compliance) -> None:
        """Refuse content that reaches past a level you are willing to accept.

        Args:
            compliance: The widest level to allow.

        Raises:
            LimitError: carrying every bound the content passes at or beyond ``compliance``.
        """
        require(beyond(self.exceeded(), compliance))

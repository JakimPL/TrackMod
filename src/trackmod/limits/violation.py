from pydantic import BaseModel

from trackmod.limits.bound import Bound
from trackmod.limits.capability import Capability
from trackmod.limits.compliance import Compliance
from trackmod.schema.config import FROZEN


class Violation(BaseModel):
    """One value that falls outside a format's bound, with the subject that carried it.

    Args:
        capability: Which quantity this is, named the same way by every format.
        value: The value the song carried.
        bound: The range the format allows at ``level``.
        level: The widest ceiling the value passed, which says who will still read the file back. A
            ``CANONICAL`` violation is refused by the tracker the format names while its descendants
            play it; an ``EXTENDED`` one is refused by those descendants too; a ``STRUCTURAL`` one has
            no bytes to sit in at all.
        subject: What carried the value, such as ``song`` or ``pattern 3``.

    Example:
        >>> from trackmod import Compliance, Violation
        >>> from trackmod.limits.bound import Bound
        >>> from trackmod.limits.capability import Capability
        >>> print(Violation(capability=Capability.TEMPO, value=441, subject="song",
        ...                 bound=Bound(minimum=32, maximum=255), level=Compliance.STRUCTURAL))
        song: tempo is 441, outside 32..255 (structural)
    """

    model_config = FROZEN

    capability: Capability
    value: int
    bound: Bound
    level: Compliance
    subject: str

    def __str__(self) -> str:
        return f"{self.subject}: {self.capability} is {self.value}, outside {self.bound} ({self.level})"

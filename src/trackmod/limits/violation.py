from pydantic import BaseModel

from trackmod.limits.bound import Bound
from trackmod.limits.capability import Capability
from trackmod.limits.compliance import Compliance
from trackmod.schema.config import FROZEN


class Violation(BaseModel):
    """One value that falls outside a format's bound, with the subject that carried it.

    ``level`` is the ceiling the value passed, which is what says who will still read the file back: a
    ``CANONICAL`` violation is one the tracker the format names refuses while its descendants play it,
    an ``EXTENDED`` one is refused by those descendants too, and a ``STRUCTURAL`` one has no bytes to
    sit in at all.
    """

    model_config = FROZEN

    capability: Capability
    value: int
    bound: Bound
    level: Compliance
    subject: str

    def __str__(self) -> str:
        return f"{self.subject}: {self.capability} is {self.value}, outside {self.bound} ({self.level})"

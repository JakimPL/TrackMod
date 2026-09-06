from enum import StrEnum, unique

from pydantic import BaseModel

from trackmod.schema.config import FROZEN


@unique
class Evidence(StrEnum):
    """How a file says which program wrote it, which is what says how far the answer reaches.

    A format that spends a field on a name answers the question directly. A format that spends a number
    answers it as far as the numbers programs took for themselves reach, and one that spends a tag on
    the layout answers it only as far as the family that settled the layout.
    """

    NAMED = "named"
    SIGNED = "signed"
    NUMBERED = "numbered"
    TAGGED = "tagged"


class Provenance(BaseModel):
    """What a file states about the program that wrote it.

    ``stated`` is the field as the file holds it, spelled the way that field spells it, so a caller
    showing the raw evidence has it. ``tracker`` is the program or family that statement names, where
    this library reads one, and ``evidence`` says which kind of statement it was — which is what tells a
    name a file spells outright from a family a layout tag implies.
    """

    model_config = FROZEN

    evidence: Evidence
    stated: str
    tracker: str | None

    def __str__(self) -> str:
        return self.tracker or self.stated

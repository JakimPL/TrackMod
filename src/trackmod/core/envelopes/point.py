from pydantic import BaseModel

from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Tick


class EnvelopePoint(BaseModel):
    """One breakpoint: the value the envelope reaches at ``tick``, interpolated from the point before.

    A point sharing its tick with the point before it is reached at once, stating a step in the curve.
    """

    model_config = FROZEN

    tick: Tick
    value: int

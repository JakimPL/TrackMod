from pydantic import BaseModel

from trackmod.limits.bound import Bound
from trackmod.limits.compliance import Compliance
from trackmod.schema.config import FROZEN


class Tier(BaseModel):
    """One of the three ceilings a capability states, and the level a value passing it breaks."""

    model_config = FROZEN

    level: Compliance
    bound: Bound

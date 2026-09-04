from __future__ import annotations

from typing import Final

from pydantic import BaseModel

from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import VibratoUnit


class Vibrato(BaseModel):
    """The auto-vibrato an Impulse Tracker sample header carries in its own right."""

    model_config = FROZEN

    speed: VibratoUnit
    depth: VibratoUnit
    rate: VibratoUnit
    waveform: VibratoUnit


NO_VIBRATO: Final[Vibrato] = Vibrato(speed=0, depth=0, rate=0, waveform=0)

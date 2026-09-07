from pydantic import BaseModel

from trackmod.core.samples.vibrato import NO_VIBRATO, Vibrato
from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Panning, Volume
from trackmod.spec.levels import MAX_VOLUME


class WaveSettings(BaseModel):
    """How a tracker sounds a waveform, beside the frames the file stores.

    A RIFF file states its frames and little else, so a tracker writing one adds a chunk of its own for
    the level, position, auto-vibrato and names its sample header would have carried. A file arriving
    from anywhere else states none of that, and the defaults here are what such a file sounds at: full
    level, wherever the channel places it, and a plain waveform under an empty name.
    """

    model_config = FROZEN

    volume: Volume = MAX_VOLUME
    gain: Volume = MAX_VOLUME
    panning: Panning | None = None
    vibrato: Vibrato = NO_VIBRATO
    name: str = ""
    filename: str = ""

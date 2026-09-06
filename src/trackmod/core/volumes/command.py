from enum import IntEnum, unique

from pydantic import BaseModel

from trackmod.limits.capability import Capability
from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Volume, VolumeAmount


@unique
class VolumeEffect(IntEnum):
    """A volume-column entry that acts on the playing voice instead of setting its level.

    A format carrying a volume column divides its byte into runs, one run per effect, and the shared
    numbering does the same past the level range -- so a volume column holds either a level or a command
    with its amount in one integer. The value here is the run each effect occupies.
    """

    FINE_VOLUME_UP = 0
    FINE_VOLUME_DOWN = 1
    VOLUME_SLIDE_UP = 2
    VOLUME_SLIDE_DOWN = 3
    PITCH_SLIDE_UP = 4
    PITCH_SLIDE_DOWN = 5
    PORTAMENTO = 6
    VIBRATO_DEPTH = 7
    VIBRATO_SPEED = 8
    PANNING = 9
    PANNING_SLIDE_LEFT = 10
    PANNING_SLIDE_RIGHT = 11

    @property
    def capability(self) -> Capability:
        """The quantity this effect's amount is held to, which each format states its own room for.

        Panning names a position across the stereo field and every other effect names a rate or a depth,
        so the two are bounded apart: Impulse Tracker counts sixty-five positions and ten rates.
        """
        match self:
            case VolumeEffect.PANNING:
                return Capability.VOLUME_PANNING
            case _:
                return Capability.VOLUME_COMMAND


class VolumeCommand(BaseModel):
    """One volume-column entry acting on the playing voice: what it does, and by how much.

    ``amount`` is stated on the grid the format's own column counts in -- Impulse Tracker's rates run to
    nine and FastTracker 2's to fifteen -- so a stored column reads back as the value it holds and each
    format's specification names the room it leaves.
    """

    model_config = FROZEN

    effect: VolumeEffect
    amount: VolumeAmount


VolumeValue = Volume | VolumeCommand

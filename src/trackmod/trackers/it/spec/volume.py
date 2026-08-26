from typing import Final

from trackmod.binary.volume import VolumeColumn, VolumeSpan
from trackmod.core.volumes.command import VolumeEffect
from trackmod.limits.bound import Bound
from trackmod.spec.levels import MAX_VOLUME
from trackmod.trackers.it.spec.ranges import MAX_VOLUME_COMMAND, MAX_VOLUME_PANNING

LEVEL_BASE: Final = 0
COMMAND_AMOUNTS: Final = Bound(minimum=0, maximum=MAX_VOLUME_COMMAND)
PANNING_AMOUNTS: Final = Bound(minimum=0, maximum=MAX_VOLUME_PANNING)

VOLUME_COLUMN: Final = VolumeColumn(
    level_base=LEVEL_BASE,
    levels=Bound(minimum=0, maximum=MAX_VOLUME),
    absent=None,
    spans=(
        VolumeSpan(effect=VolumeEffect.FINE_VOLUME_UP, base=65, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.FINE_VOLUME_DOWN, base=75, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.VOLUME_SLIDE_UP, base=85, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.VOLUME_SLIDE_DOWN, base=95, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.PITCH_SLIDE_DOWN, base=105, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.PITCH_SLIDE_UP, base=115, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.PANNING, base=128, amounts=PANNING_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.PORTAMENTO, base=193, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.VIBRATO_DEPTH, base=203, amounts=COMMAND_AMOUNTS),
    ),
)

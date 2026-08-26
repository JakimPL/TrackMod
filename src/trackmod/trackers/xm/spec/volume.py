from typing import Final

from trackmod.binary.volume import VolumeColumn, VolumeSpan
from trackmod.core.volumes.command import VolumeEffect
from trackmod.limits.bound import Bound
from trackmod.spec.levels import MAX_VOLUME
from trackmod.trackers.xm.spec.cells import VOLUME_COLUMN_BASE, VOLUME_COLUMN_EMPTY
from trackmod.trackers.xm.spec.ranges import MAX_VOLUME_COMMAND, MAX_VOLUME_PANNING

COMMAND_AMOUNTS: Final = Bound(minimum=0, maximum=MAX_VOLUME_COMMAND)
PANNING_AMOUNTS: Final = Bound(minimum=0, maximum=MAX_VOLUME_PANNING)

VOLUME_COLUMN: Final = VolumeColumn(
    level_base=VOLUME_COLUMN_BASE,
    levels=Bound(minimum=0, maximum=MAX_VOLUME),
    absent=VOLUME_COLUMN_EMPTY,
    spans=(
        VolumeSpan(effect=VolumeEffect.VOLUME_SLIDE_DOWN, base=0x60, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.VOLUME_SLIDE_UP, base=0x70, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.FINE_VOLUME_DOWN, base=0x80, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.FINE_VOLUME_UP, base=0x90, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.VIBRATO_SPEED, base=0xA0, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.VIBRATO_DEPTH, base=0xB0, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.PANNING, base=0xC0, amounts=PANNING_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.PANNING_SLIDE_LEFT, base=0xD0, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.PANNING_SLIDE_RIGHT, base=0xE0, amounts=COMMAND_AMOUNTS),
        VolumeSpan(effect=VolumeEffect.PORTAMENTO, base=0xF0, amounts=COMMAND_AMOUNTS),
    ),
)

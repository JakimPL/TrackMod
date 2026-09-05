from typing import Final

from trackmod.binary.volume import VolumeColumn, VolumeSpan
from trackmod.core.volumes.command import VolumeEffect
from trackmod.limits.bound import Bound
from trackmod.spec.levels import MAX_VOLUME
from trackmod.trackers.s3m.spec.ranges import MAX_VOLUME_PANNING

LEVEL_BASE: Final = 0
PANNING_BASE: Final = 128
PANNING_AMOUNTS: Final = Bound(minimum=0, maximum=MAX_VOLUME_PANNING)

VOLUME_COLUMN: Final = VolumeColumn(
    level_base=LEVEL_BASE,
    levels=Bound(minimum=0, maximum=MAX_VOLUME),
    absent=None,
    spans=(VolumeSpan(effect=VolumeEffect.PANNING, base=PANNING_BASE, amounts=PANNING_AMOUNTS),),
)

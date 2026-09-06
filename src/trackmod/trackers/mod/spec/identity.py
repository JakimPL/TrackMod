from typing import Final

from trackmod.trackers.amiga.spec.sizes import MODULE_NAME_BYTES, ORDER_TABLE_BYTES
from trackmod.trackers.mod.spec.sizes import SAMPLE_TABLE_BYTES

EXTENSION: Final = ".mod"

TAG_BYTES: Final = 4
TAG_OFFSET: Final = MODULE_NAME_BYTES + SAMPLE_TABLE_BYTES + 2 + ORDER_TABLE_BYTES

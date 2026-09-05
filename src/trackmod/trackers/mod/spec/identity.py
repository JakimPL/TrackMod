from typing import Final

from trackmod.trackers.mod.spec.sizes import (
    MODULE_NAME_BYTES,
    ORDER_TABLE_BYTES,
    SAMPLE_TABLE_BYTES,
)

EXTENSION: Final = ".mod"

TAG_BYTES: Final = 4
TAG_OFFSET: Final = MODULE_NAME_BYTES + SAMPLE_TABLE_BYTES + 2 + ORDER_TABLE_BYTES

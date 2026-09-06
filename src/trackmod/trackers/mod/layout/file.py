from typing import Final

from trackmod.binary.records.field import Field
from trackmod.binary.records.record import Record
from trackmod.trackers.amiga.spec.sizes import ORDER_TABLE_BYTES
from trackmod.trackers.mod.spec.identity import TAG_BYTES
from trackmod.trackers.mod.spec.sizes import SEQUENCE_BYTES

SEQUENCE: Final = Record(
    size=SEQUENCE_BYTES,
    fields=(
        Field(name="order_count", offset=0, code="B"),
        Field(name="restart", offset=1, code="B"),
        Field(name="orders", offset=2, code=f"{ORDER_TABLE_BYTES}s"),
        Field(name="tag", offset=2 + ORDER_TABLE_BYTES, code=f"{TAG_BYTES}s"),
    ),
)

from typing import Final

from trackmod.binary.records.field import Field
from trackmod.binary.records.record import Record
from trackmod.trackers.amiga.spec.sizes import MODULE_NAME_BYTES

MODULE_NAME: Final = Record(
    size=MODULE_NAME_BYTES,
    fields=(Field(name="name", offset=0, code=f"{MODULE_NAME_BYTES}s"),),
)

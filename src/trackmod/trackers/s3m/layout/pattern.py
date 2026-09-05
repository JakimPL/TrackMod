from typing import Final

from trackmod.binary.records.field import Field
from trackmod.binary.records.record import Record
from trackmod.trackers.s3m.spec.sizes import PATTERN_LENGTH_BYTES

PATTERN_HEADER: Final = Record(
    size=PATTERN_LENGTH_BYTES,
    fields=(Field(name="block_size", offset=0, code="<H"),),
)

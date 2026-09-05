from typing import Final

from trackmod.binary.records.field import Field
from trackmod.binary.records.record import Record
from trackmod.trackers.mod.spec.sizes import NAME_BYTES, SAMPLE_RECORD_BYTES

SAMPLE_HEADER: Final = Record(
    size=SAMPLE_RECORD_BYTES,
    fields=(
        Field(name="name", offset=0, code=f"{NAME_BYTES}s"),
        Field(name="length", offset=22, code=">H"),
        Field(name="finetune", offset=24, code="B"),
        Field(name="volume", offset=25, code="B"),
        Field(name="loop_begin", offset=26, code=">H"),
        Field(name="loop_length", offset=28, code=">H"),
    ),
)

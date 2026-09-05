from typing import Final

from trackmod.binary.records.field import Field
from trackmod.binary.records.record import Record
from trackmod.trackers.s3m.spec.sizes import (
    FILENAME_BYTES,
    INSTRUMENT_RECORD_BYTES,
    NAME_BYTES,
)

INSTRUMENT_RECORD: Final = Record(
    size=INSTRUMENT_RECORD_BYTES,
    fields=(
        Field(name="type", offset=0, code="B"),
        Field(name="filename", offset=1, code=f"{FILENAME_BYTES}s"),
        Field(name="frames_high", offset=13, code="B"),
        Field(name="frames_low", offset=14, code="<H"),
        Field(name="length", offset=16, code="<I"),
        Field(name="loop_begin", offset=20, code="<I"),
        Field(name="loop_end", offset=24, code="<I"),
        Field(name="volume", offset=28, code="B"),
        Field(name="pack", offset=30, code="B"),
        Field(name="flags", offset=31, code="B"),
        Field(name="c2spd", offset=32, code="<I"),
        Field(name="name", offset=48, code=f"{NAME_BYTES}s"),
        Field(name="magic", offset=76, code="4s"),
    ),
)

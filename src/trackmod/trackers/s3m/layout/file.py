from typing import Final

from trackmod.binary.records.field import Field
from trackmod.binary.records.record import Record
from trackmod.trackers.s3m.spec.sizes import (
    CHANNELS_STORED,
    FILE_HEADER_BYTES,
    NAME_BYTES,
)

FILE_HEADER: Final = Record(
    size=FILE_HEADER_BYTES,
    fields=(
        Field(name="name", offset=0, code=f"{NAME_BYTES}s"),
        Field(name="end_of_text", offset=28, code="B"),
        Field(name="type", offset=29, code="B"),
        Field(name="order_count", offset=32, code="<H"),
        Field(name="sample_count", offset=34, code="<H"),
        Field(name="pattern_count", offset=36, code="<H"),
        Field(name="flags", offset=38, code="<H"),
        Field(name="created_with", offset=40, code="<H"),
        Field(name="frame_format", offset=42, code="<H"),
        Field(name="magic", offset=44, code="4s"),
        Field(name="global_volume", offset=48, code="B"),
        Field(name="speed", offset=49, code="B"),
        Field(name="tempo", offset=50, code="B"),
        Field(name="mix_volume", offset=51, code="B"),
        Field(name="click_removal", offset=52, code="B"),
        Field(name="default_panning", offset=53, code="B"),
        Field(name="special", offset=62, code="<H"),
        Field(name="channel_settings", offset=64, code=f"{CHANNELS_STORED}s"),
    ),
)

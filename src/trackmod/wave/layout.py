from typing import Final

from trackmod.binary.records.field import Field
from trackmod.binary.records.record import Record
from trackmod.wave.spec import (
    CHUNK_HEADER_BYTES,
    EXTRA_CHUNK_BYTES,
    FORMAT_CHUNK_BYTES,
    INSTRUMENT_CHUNK_BYTES,
    SAMPLER_CHUNK_BYTES,
    SAMPLER_LOOP_BYTES,
    TAG_BYTES,
)

CHUNK_HEADER: Final = Record(
    size=CHUNK_HEADER_BYTES,
    fields=(
        Field(name="tag", offset=0, code=f"{TAG_BYTES}s"),
        Field(name="size", offset=4, code="<I"),
    ),
)

FORMAT_CHUNK: Final = Record(
    size=FORMAT_CHUNK_BYTES,
    fields=(
        Field(name="encoding", offset=0, code="<H"),
        Field(name="channels", offset=2, code="<H"),
        Field(name="rate", offset=4, code="<I"),
        Field(name="byte_rate", offset=8, code="<I"),
        Field(name="block_align", offset=12, code="<H"),
        Field(name="bits", offset=14, code="<H"),
    ),
)

SAMPLER_CHUNK: Final = Record(
    size=SAMPLER_CHUNK_BYTES,
    fields=(
        Field(name="manufacturer", offset=0, code="<I"),
        Field(name="product", offset=4, code="<I"),
        Field(name="period", offset=8, code="<I"),
        Field(name="base_note", offset=12, code="<I"),
        Field(name="pitch_fraction", offset=16, code="<I"),
        Field(name="smpte_format", offset=20, code="<I"),
        Field(name="smpte_offset", offset=24, code="<I"),
        Field(name="loops", offset=28, code="<I"),
        Field(name="sampler_bytes", offset=32, code="<I"),
    ),
)

SAMPLER_LOOP: Final = Record(
    size=SAMPLER_LOOP_BYTES,
    fields=(
        Field(name="identifier", offset=0, code="<I"),
        Field(name="mode", offset=4, code="<I"),
        Field(name="begin", offset=8, code="<I"),
        Field(name="end", offset=12, code="<I"),
        Field(name="fraction", offset=16, code="<I"),
        Field(name="plays", offset=20, code="<I"),
    ),
)

INSTRUMENT_CHUNK: Final = Record(
    size=INSTRUMENT_CHUNK_BYTES,
    fields=(
        Field(name="unshifted_note", offset=0, code="B"),
        Field(name="finetune", offset=1, code="b"),
        Field(name="gain", offset=2, code="b"),
        Field(name="low_note", offset=3, code="B"),
        Field(name="high_note", offset=4, code="B"),
        Field(name="low_velocity", offset=5, code="B"),
        Field(name="high_velocity", offset=6, code="B"),
    ),
)

EXTRA_CHUNK: Final = Record(
    size=EXTRA_CHUNK_BYTES,
    fields=(
        Field(name="flags", offset=0, code="<I"),
        Field(name="panning", offset=4, code="<H"),
        Field(name="volume", offset=6, code="<H"),
        Field(name="gain", offset=8, code="<H"),
        Field(name="reserved", offset=10, code="<H"),
        Field(name="vibrato_type", offset=12, code="B"),
        Field(name="vibrato_sweep", offset=13, code="B"),
        Field(name="vibrato_depth", offset=14, code="B"),
        Field(name="vibrato_rate", offset=15, code="B"),
    ),
)

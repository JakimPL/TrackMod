from trackmod.trackers.s3m.layout.file import FILE_HEADER
from trackmod.trackers.s3m.layout.instrument import INSTRUMENT_RECORD
from trackmod.trackers.s3m.layout.pattern import PATTERN_HEADER
from trackmod.trackers.s3m.spec.sizes import (
    FILE_HEADER_BYTES,
    INSTRUMENT_RECORD_BYTES,
    PARAGRAPH_BYTES,
    PATTERN_LENGTH_BYTES,
)


def test_each_record_is_the_size_this_format_lays_out() -> None:
    assert FILE_HEADER.size == FILE_HEADER_BYTES
    assert INSTRUMENT_RECORD.size == INSTRUMENT_RECORD_BYTES
    assert PATTERN_HEADER.size == PATTERN_LENGTH_BYTES


def test_an_instrument_record_spans_a_whole_number_of_paragraphs() -> None:
    assert INSTRUMENT_RECORD_BYTES % PARAGRAPH_BYTES == 0


def test_every_described_field_stays_inside_the_record_it_belongs_to() -> None:
    for record in (FILE_HEADER, INSTRUMENT_RECORD, PATTERN_HEADER):
        for field in record.fields:
            assert field.offset + field.size <= record.size


def test_a_record_reads_back_the_values_it_was_packed_with() -> None:
    values = {field.name: 0 if field.code[-1] != "s" else b"" for field in INSTRUMENT_RECORD.fields}
    values["length"] = 4096
    values["c2spd"] = 44100
    values["name"] = b"probe"
    packed = INSTRUMENT_RECORD.pack(values)
    read = INSTRUMENT_RECORD.unpack(packed)
    assert read["length"] == 4096
    assert read["c2spd"] == 44100
    assert read["name"].startswith(b"probe")

from trackmod.trackers.s3m.layout.file import FILE_HEADER
from trackmod.trackers.s3m.layout.instrument import INSTRUMENT_RECORD
from trackmod.trackers.s3m.layout.pattern import PATTERN_HEADER
from trackmod.trackers.s3m.spec.sizes import INSTRUMENT_RECORD_BYTES, PARAGRAPH_BYTES

# The sizes here are written out as the numbers this format's own records have rather than imported
# from the constants that state them, so a record laid out a byte adrift disagrees with the tracker
# rather than agreeing with itself.

RECORDS = (
    (FILE_HEADER, 96),
    (INSTRUMENT_RECORD, 80),
    (PATTERN_HEADER, 2),
)

TEXT_FIELDS = (
    (FILE_HEADER, "name", 28),
    (INSTRUMENT_RECORD, "name", 28),
    (INSTRUMENT_RECORD, "filename", 12),
)


def test_each_record_is_the_size_this_format_lays_out() -> None:
    assert all(record.size == size for record, size in RECORDS)


def test_the_text_a_record_carries_fills_the_room_its_tracker_gave_it() -> None:
    # A name is what a tracker showed in its sample list and a filename what the system of the day
    # allowed, so both are as long as the record they sit in rather than as long as the text.
    for record, name, size in TEXT_FIELDS:
        (field,) = (field for field in record.fields if field.name == name)
        assert field.size == size


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

from trackmod.binary.records.record import Record
from trackmod.trackers.xm.layout.envelope import (
    ENVELOPE_KINDS,
    POINTS_OFFSETS,
    envelope_field,
)
from trackmod.trackers.xm.layout.file import FILE_HEADER
from trackmod.trackers.xm.layout.instrument import (
    EMPTY_INSTRUMENT_HEADER,
    INSTRUMENT_FILE_HEADER,
    INSTRUMENT_HEADER,
)
from trackmod.trackers.xm.layout.pattern import PATTERN_HEADER
from trackmod.trackers.xm.layout.sample import SAMPLE_HEADER
from trackmod.trackers.xm.spec.identity import MAGIC, MAGIC_BYTES
from trackmod.trackers.xm.spec.sizes import (
    FILE_HEADER_BYTES,
    HEADER_SIZE_FIELD,
    HEADER_SIZE_OFFSET,
    ORDER_TABLE_BYTES,
)

# Every size here is written out as the number this format's headers have rather than imported from
# the constant that states it, so a record laid out a byte adrift disagrees with the tracker rather
# than agreeing with itself.

RECORDS = (
    (FILE_HEADER, 80),
    (PATTERN_HEADER, 9),
    (SAMPLE_HEADER, 40),
    (INSTRUMENT_HEADER, 263),
    (EMPTY_INSTRUMENT_HEADER, 29),
    (INSTRUMENT_FILE_HEADER, 298),
)


def occupied_bytes(record: Record) -> set[int]:
    spans = [range(field.offset, field.offset + field.size) for field in record.fields]
    spans += [range(array.offset, array.offset + array.size) for array in record.arrays]
    occupied: set[int] = set()
    for span in spans:
        assert not set(span) & occupied
        occupied |= set(span)

    return occupied


def test_each_record_is_the_size_this_format_lays_it_out_at() -> None:
    assert all(record.size == size for record, size in RECORDS)


def test_no_two_fields_of_a_record_overlap() -> None:
    for record, _ in RECORDS:
        occupied_bytes(record)


def test_the_declared_header_size_covers_the_order_table_and_what_precedes_it() -> None:
    # The field counts from where it sits, so the first pattern begins exactly this far into the file.
    assert HEADER_SIZE_OFFSET + HEADER_SIZE_FIELD == FILE_HEADER_BYTES + ORDER_TABLE_BYTES


def test_the_module_tag_fills_the_field_that_carries_it() -> None:
    assert len(MAGIC) == MAGIC_BYTES


def test_the_short_instrument_header_is_the_opening_of_the_long_one() -> None:
    short = {(field.name, field.offset, field.code) for field in EMPTY_INSTRUMENT_HEADER.fields}
    long = {(field.name, field.offset, field.code) for field in INSTRUMENT_HEADER.fields}
    assert short <= long


def test_each_envelope_has_its_own_point_table() -> None:
    assert len({POINTS_OFFSETS[kind] for kind in ENVELOPE_KINDS}) == len(ENVELOPE_KINDS)
    names = {envelope_field(kind, "flags") for kind in ENVELOPE_KINDS}
    assert names <= {field.name for field in INSTRUMENT_HEADER.fields}

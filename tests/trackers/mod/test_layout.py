from trackmod.binary.records.record import Record
from trackmod.trackers.mod.layout.file import MODULE_NAME, SEQUENCE
from trackmod.trackers.mod.layout.sample import SAMPLE_HEADER
from trackmod.trackers.mod.spec.identity import TAG_BYTES, TAG_OFFSET
from trackmod.trackers.mod.spec.sizes import (
    FILE_HEADER_BYTES,
    MODULE_NAME_BYTES,
    ORDER_TABLE_BYTES,
    SAMPLE_RECORD_BYTES,
    SAMPLE_SLOTS,
    SAMPLE_TABLE_BYTES,
    SAMPLE_TABLE_OFFSET,
    SEQUENCE_BYTES,
)

RECORDS = (
    (MODULE_NAME, MODULE_NAME_BYTES),
    (SEQUENCE, SEQUENCE_BYTES),
    (SAMPLE_HEADER, SAMPLE_RECORD_BYTES),
)

MULTI_BYTE_CODES = ("H", "I", "h", "i", "L", "l", "Q", "q")


def occupied_bytes(record: Record) -> set[int]:
    occupied: set[int] = set()
    for field in record.fields:
        span = set(range(field.offset, field.offset + field.size))
        assert not span & occupied
        occupied |= span

    return occupied


def test_record_sizes_match_the_format() -> None:
    assert all(record.size == size for record, size in RECORDS)


def test_no_two_fields_of_a_record_overlap() -> None:
    for record, _ in RECORDS:
        occupied_bytes(record)


def test_every_number_this_format_stores_is_written_high_byte_first() -> None:
    # This is the one format here that came off a big-endian machine, and a byte order read the other
    # way round would turn every length and every loop into a different number that still parses.
    for record, _ in RECORDS:
        for field in record.fields:
            if field.code[-1] in MULTI_BYTE_CODES:
                assert field.code.startswith(">")


def test_the_header_is_the_name_the_sample_table_and_the_sequence() -> None:
    # The numbers are the ones this format's header has, written out rather than imported: a title of
    # twenty bytes, thirty-one records of thirty, and the sequence that closes it.
    assert (MODULE_NAME_BYTES, SAMPLE_SLOTS, SAMPLE_RECORD_BYTES) == (20, 31, 30)
    assert MODULE_NAME_BYTES + SAMPLE_TABLE_BYTES + SEQUENCE_BYTES == FILE_HEADER_BYTES
    assert SAMPLE_TABLE_BYTES == SAMPLE_SLOTS * SAMPLE_RECORD_BYTES
    assert SAMPLE_TABLE_OFFSET == 20


def test_the_tag_closes_the_header() -> None:
    assert (TAG_OFFSET, FILE_HEADER_BYTES) == (1080, 1084)
    assert TAG_OFFSET + TAG_BYTES == FILE_HEADER_BYTES
    assert SEQUENCE_BYTES == 2 + ORDER_TABLE_BYTES + TAG_BYTES

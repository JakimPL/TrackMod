from trackmod.trackers.amiga.spec.sizes import (
    MODULE_NAME_BYTES,
    ORDER_TABLE_BYTES,
    SAMPLE_RECORD_BYTES,
)
from trackmod.trackers.st.layout.file import SEQUENCE
from trackmod.trackers.st.spec.sizes import (
    FILE_HEADER_BYTES,
    SAMPLE_SLOTS,
    SAMPLE_TABLE_BYTES,
    SEQUENCE_BYTES,
)

TEMPO_OFFSET = 1


def test_the_header_is_the_name_the_records_and_the_sequence() -> None:
    assert SAMPLE_TABLE_BYTES == SAMPLE_SLOTS * SAMPLE_RECORD_BYTES
    assert SEQUENCE_BYTES == 2 + ORDER_TABLE_BYTES
    assert FILE_HEADER_BYTES == MODULE_NAME_BYTES + SAMPLE_TABLE_BYTES + SEQUENCE_BYTES


def test_the_sequence_holds_a_speed_byte_where_the_format_after_it_holds_a_restart() -> None:
    fields = {field.name: field.offset for field in SEQUENCE.fields}
    assert fields == {"order_count": 0, "tempo": TEMPO_OFFSET, "orders": 2}
    assert SEQUENCE.size == SEQUENCE_BYTES


def test_the_records_start_where_the_name_ends() -> None:
    assert FILE_HEADER_BYTES - SEQUENCE.size == MODULE_NAME_BYTES + SAMPLE_TABLE_BYTES

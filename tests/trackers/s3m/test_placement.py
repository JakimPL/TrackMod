import pytest

from trackmod.trackers.s3m.parapointers import (
    joined_pointer,
    parapointer,
    pointed,
    split_pointer,
)
from trackmod.trackers.s3m.placement import Placement, aligned, tables_bytes
from trackmod.trackers.s3m.spec.sizes import INSTRUMENT_RECORD_BYTES, PARAGRAPH_BYTES

MEGABYTE = 1 << 20


@pytest.mark.parametrize(("offset", "boundary"), [(0, 0), (1, 16), (16, 16), (17, 32), (80, 80)])
def test_a_block_opens_on_the_paragraph_at_or_past_where_the_one_before_it_ended(offset: int, boundary: int) -> None:
    assert aligned(offset) == boundary


def test_a_pointer_names_the_paragraph_a_block_opens_on() -> None:
    assert parapointer(PARAGRAPH_BYTES * 7) == 7
    assert pointed(7) == PARAGRAPH_BYTES * 7


def test_an_offset_inside_a_paragraph_names_none() -> None:
    with pytest.raises(ValueError, match="whole ones"):
        parapointer(PARAGRAPH_BYTES + 1)


def test_a_waveform_pointer_reaches_past_the_megabyte_the_others_stop_at() -> None:
    offset = 8 * MEGABYTE
    high, low = split_pointer(offset)
    assert high > 0
    assert joined_pointer(high, low) == offset


def test_every_block_a_module_holds_lands_on_a_paragraph() -> None:
    placement = Placement.of(orders=3, patterns=[130, 64], waveforms=[300, 17])
    for offset in (*placement.instruments, *placement.patterns, *placement.waveforms):
        assert offset % PARAGRAPH_BYTES == 0


def test_the_records_sit_before_the_patterns_and_the_waveforms_after_them() -> None:
    placement = Placement.of(orders=3, patterns=[130, 64], waveforms=[300, 17])
    assert max(placement.instruments) < min(placement.patterns)
    assert max(placement.patterns) < min(placement.waveforms)
    assert placement.total >= max(placement.waveforms)


def test_the_first_record_follows_the_tables_the_header_states() -> None:
    placement = Placement.of(orders=3, patterns=[64], waveforms=[32])
    start = tables_bytes(samples=1, patterns=1, orders=3)
    assert placement.instruments == (aligned(start),)
    assert placement.patterns[0] == aligned(start) + INSTRUMENT_RECORD_BYTES

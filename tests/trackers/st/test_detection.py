import pytest

from tests.trackers.amiga.conftest import sample_record, silent_pattern
from tests.trackers.mod.conftest import raw_module as raw_protracker
from tests.trackers.st.conftest import raw_module
from trackmod.core.voices.voices import SampleVoices
from trackmod.trackers.registry import parse_voices
from trackmod.trackers.st.detection import stated_size, written_here
from trackmod.trackers.st.spec.identity import EXTENSION
from trackmod.trackers.st.spec.ranges import CHANNELS

WORDS = 8
SHARED_WORDS = 270
SHARED_SLOT = 19


def fifteen_sample_file() -> bytes:
    """A file of this format whose records add up to its own length, which is what names the layout."""
    return raw_module(
        order_count=1,
        records=(sample_record(name=b"lead", length=WORDS),),
        patterns=silent_pattern(channels=CHANNELS),
        waveforms=bytes(WORDS * 2),
    )


def test_a_file_of_this_format_is_as_long_as_its_own_records_state() -> None:
    data = fifteen_sample_file()
    assert stated_size(data) == len(data)
    assert written_here(data)


def test_a_file_stopping_inside_the_header_states_no_size() -> None:
    assert stated_size(bytes(64)) is None
    assert not written_here(bytes(64))


@pytest.mark.parametrize("extra", [1, -1, 1024])
def test_a_file_of_another_length_than_its_records_state_is_not_this_format(extra: int) -> None:
    data = fifteen_sample_file()
    stretched = data + bytes(extra) if extra > 0 else data[:extra]
    assert not written_here(stretched)


def test_a_protracker_module_is_not_read_as_this_format() -> None:
    data = raw_protracker(order_count=1, patterns=silent_pattern(channels=CHANNELS))
    assert not written_here(data)


def test_the_registry_reads_whichever_amiga_layout_the_bytes_hold() -> None:
    # Both are named with the same extension, so the bytes are what decides, and each layout reads as
    # the table its own records state.
    older = parse_voices(fifteen_sample_file(), extension=EXTENSION)
    newer = parse_voices(
        raw_protracker(order_count=1, patterns=silent_pattern(channels=CHANNELS)),
        extension=EXTENSION,
    )
    assert isinstance(older, SampleVoices)
    assert isinstance(newer, SampleVoices)
    assert len(older.samples) == 1
    assert newer.samples == ()


def ambiguous_module() -> bytes:
    """A tagged module as long as both readings state, which real collections hold.

    A tagged module keeps its sixteenth record where the older layout keeps its order table, so the two
    readings can land on the same length: one pattern and a waveform of the right size add up to a whole
    number of the older layout's patterns behind its shorter header. Only the tag tells them apart.
    """
    records = tuple(sample_record() for _ in range(SHARED_SLOT)) + (sample_record(length=SHARED_WORDS),)
    return raw_protracker(
        order_count=1,
        orders=bytes(1),
        records=records,
        patterns=silent_pattern(channels=CHANNELS),
        waveforms=bytes(SHARED_WORDS * 2),
    )


def test_a_module_can_add_up_both_ways_at_once() -> None:
    data = ambiguous_module()
    assert stated_size(data) == len(data)


def test_a_tagged_module_is_read_under_its_tag_where_both_readings_add_up() -> None:
    # A tag is what a file states about itself, so it settles the reading. The older layout is the one
    # that states no tag at all, which is why its arithmetic alone never decides against one.
    data = ambiguous_module()
    voices = parse_voices(data, extension=EXTENSION)
    assert len(voices.samples) == SHARED_SLOT + 1

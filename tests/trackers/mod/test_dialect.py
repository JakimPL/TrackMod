import pytest

from tests.trackers.mod.conftest import raw_module
from trackmod.trackers.mod.dialect import (
    DEFAULT_DIALECT,
    DIALECTS,
    GENERATED,
    NAMED,
    WIDE_DIALECT,
    channel_tag,
)
from trackmod.trackers.mod.spec.dialects import SPLIT_TAGS
from trackmod.trackers.mod.spec.identity import TAG_BYTES, TAG_OFFSET
from trackmod.trackers.mod.spec.ranges import (
    CANONICAL_CHANNELS,
    EXTENDED_MIN_CHANNELS,
    STRUCTURAL_MAX_CHANNELS,
    TAGGED_MAX_PATTERNS,
)
from trackmod.trackers.mod.tag import chosen, detected, stated_tag


def test_every_tag_fills_the_field_that_carries_it() -> None:
    assert all(len(dialect.tag) == TAG_BYTES for dialect in DIALECTS.values())


def test_no_two_dialects_claim_one_tag() -> None:
    stated = [dialect.tag for dialect in (*GENERATED, *NAMED)]
    assert len(set(stated)) == len(stated)


def test_the_generated_families_cover_every_width_the_format_reaches() -> None:
    widths = {
        DIALECTS[channel_tag(channels)].channels
        for channels in range(EXTENDED_MIN_CHANNELS, STRUCTURAL_MAX_CHANNELS + 1)
    }
    assert widths == set(range(EXTENDED_MIN_CHANNELS, STRUCTURAL_MAX_CHANNELS + 1))


def test_the_tag_is_read_from_the_end_of_the_header() -> None:
    data = raw_module(tag=b"6CHN")
    assert stated_tag(data) == b"6CHN"
    assert data[TAG_OFFSET : TAG_OFFSET + TAG_BYTES] == b"6CHN"


def test_a_tag_settles_the_width_before_a_pattern_is_read() -> None:
    assert detected(raw_module(tag=b"M.K.")).channels == CANONICAL_CHANNELS
    assert detected(raw_module(tag=b"6CHN")).channels == 6
    assert detected(raw_module(tag=b"16CH")).channels == 16
    assert detected(raw_module(tag=b"TDZ2")).channels == 2
    assert detected(raw_module(tag=b"CD81")).channels == 8


def test_a_split_pattern_layout_is_named_when_it_is_refused() -> None:
    tag = next(iter(SPLIT_TAGS))
    with pytest.raises(ValueError, match="two four-channel"):
        detected(raw_module(tag=tag))


def test_a_tag_no_dialect_states_is_refused() -> None:
    with pytest.raises(ValueError, match="none of the dialects"):
        detected(raw_module(tag=b"\0\0\0\0"))


def test_a_file_stopping_inside_the_header_is_refused() -> None:
    with pytest.raises(ValueError, match="header"):
        detected(raw_module()[:100])


def test_four_channels_are_written_under_the_tag_the_original_tracker_wrote() -> None:
    assert chosen(channels=CANONICAL_CHANNELS, patterns=TAGGED_MAX_PATTERNS) is DEFAULT_DIALECT
    assert chosen(channels=CANONICAL_CHANNELS, patterns=TAGGED_MAX_PATTERNS + 1) is WIDE_DIALECT


def test_another_width_is_written_under_the_family_that_spells_it() -> None:
    assert chosen(channels=6, patterns=1).tag == b"6CHN"
    assert chosen(channels=12, patterns=1).tag == b"12CH"


def test_a_width_no_dialect_states_is_refused() -> None:
    with pytest.raises(ValueError, match="no dialect states"):
        chosen(channels=STRUCTURAL_MAX_CHANNELS + 1, patterns=1)

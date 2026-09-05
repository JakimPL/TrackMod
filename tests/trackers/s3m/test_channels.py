import pytest

from trackmod.trackers.s3m.channels import channel_table, placed, sounded, stated_width
from trackmod.trackers.s3m.spec.flags import CHANNEL_MUTED, CHANNEL_UNUSED
from trackmod.trackers.s3m.spec.sizes import CHANNELS_STORED

OPENING_SLOTS = (0, 8, 1, 9, 2, 10, 3, 11)


def test_a_module_opens_with_its_channels_laid_out_side_by_side() -> None:
    assert tuple(placed(channel) for channel in range(len(OPENING_SLOTS))) == OPENING_SLOTS


def test_the_table_names_a_slot_for_each_channel_and_leaves_the_rest_out() -> None:
    table = channel_table(4)
    assert len(table) == CHANNELS_STORED
    assert table[:4] == OPENING_SLOTS[:4]
    assert set(table[4:]) == {CHANNEL_UNUSED}


@pytest.mark.parametrize("channels", [1, 4, 16, 32])
def test_the_width_a_table_states_is_the_width_it_was_built_at(channels: int) -> None:
    assert stated_width(channel_table(channels)) == channels


def test_a_muted_channel_is_stated_and_silent() -> None:
    assert sounded(0)
    assert not sounded(CHANNEL_UNUSED)
    assert not sounded(CHANNEL_MUTED | 4)

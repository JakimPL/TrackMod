import pytest

from trackmod.trackers.it.panning import shared_panning, stored_panning
from trackmod.trackers.it.settings import ITSettings

# This format holds a channel anywhere across sixty-five positions, so the shared 0..255 range lands on
# it four steps at a time. The numbers below are those positions, stated rather than computed.

CENTRE = 32
FULL_VOLUME = 64
CHANNELS = 64

STORED = ((0, 0), (2, 1), (128, 32), (255, 64))
SHARED = ((0, 0), (32, 128), (64, 255))


@pytest.mark.parametrize(("panning", "stored"), STORED)
def test_a_shared_position_lands_on_the_position_this_format_stores(panning: int, stored: int) -> None:
    assert stored_panning(panning) == stored


@pytest.mark.parametrize(("stored", "panning"), SHARED)
def test_a_stored_position_opens_back_onto_the_shared_range(stored: int, panning: int) -> None:
    assert shared_panning(stored) == panning


def test_a_module_stating_nothing_opens_every_channel_centred_and_at_full_volume() -> None:
    # The header carries a table per channel whatever a song says about them, so the values a tracker
    # fills them with are what a module built from nothing states.
    settings = ITSettings()
    assert settings.channel_panning == (CENTRE,) * CHANNELS
    assert settings.channel_volume == (FULL_VOLUME,) * CHANNELS

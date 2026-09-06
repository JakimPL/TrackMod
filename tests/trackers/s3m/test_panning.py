import pytest

from trackmod.trackers.s3m.panning import shared_panning, stored_panning, stored_position

# A channel's table entry holds sixteen positions and the effect that moves it mid-song counts in a
# hundred and twenty-nine, so the shared 0..255 range lands on each of them differently. The numbers
# below are those positions, stated rather than computed: rounding a centred channel down instead of to
# the nearest of them would open it at 119 of 255.

STORED = ((0, 0), (128, 8), (255, 15))
SHARED = ((0, 0), (8, 136), (15, 255))
POSITIONS = ((0, 0), (1, 1), (128, 64), (255, 128))


@pytest.mark.parametrize(("panning", "stored"), STORED)
def test_a_shared_position_lands_on_the_nearest_of_the_sixteen_a_channel_states(panning: int, stored: int) -> None:
    assert stored_panning(panning) == stored


@pytest.mark.parametrize(("stored", "panning"), SHARED)
def test_a_stored_position_opens_back_onto_the_shared_range(stored: int, panning: int) -> None:
    assert shared_panning(stored) == panning


@pytest.mark.parametrize(("panning", "position"), POSITIONS)
def test_the_effect_that_moves_a_channel_counts_in_the_finer_of_the_two_steps(panning: int, position: int) -> None:
    assert stored_position(panning) == position

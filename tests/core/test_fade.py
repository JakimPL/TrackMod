import math

import pytest

from trackmod.core.instruments.fade import fade_seconds, fade_ticks, fadeout_value
from trackmod.core.timing.clock import tick_seconds
from trackmod.spec.levels import NO_FADEOUT
from trackmod.trackers.it import fade as it_fade
from trackmod.trackers.it.spec.ranges import CANONICAL_MAX_FADEOUT as IT_MAX_FADEOUT
from trackmod.trackers.it.spec.ranges import FADE_COUNTER as IT_COUNTER
from trackmod.trackers.xm import fade as xm_fade
from trackmod.trackers.xm.spec.ranges import CANONICAL_MAX_FADEOUT as XM_MAX_FADEOUT
from trackmod.trackers.xm.spec.ranges import FADE_COUNTER as XM_COUNTER

TEMPO = 125
COUNTER = 1024
FASTEST_CANONICAL_TICKS = 8


@pytest.mark.parametrize(("fadeout", "ticks"), [(8, 128.0), (32, 32.0), (128, 8.0), (256, 4.0)])
def test_a_fade_lasts_the_counter_divided_by_the_rate(fadeout: int, ticks: float) -> None:
    assert fade_ticks(fadeout, counter=COUNTER) == pytest.approx(ticks)


def test_an_instrument_stating_no_fade_holds_its_voice() -> None:
    assert fade_ticks(NO_FADEOUT, counter=COUNTER) == math.inf


def test_a_fade_in_seconds_is_its_ticks_on_the_clock() -> None:
    assert fade_seconds(32, counter=COUNTER, tempo=TEMPO) == pytest.approx(32 * tick_seconds(TEMPO))


def test_a_rate_running_backwards_is_refused() -> None:
    with pytest.raises(ValueError):
        fade_ticks(-1, counter=COUNTER)


def test_an_empty_counter_is_refused() -> None:
    with pytest.raises(ValueError):
        fade_ticks(32, counter=0)


@pytest.mark.parametrize("seconds", [0.16, 0.64, 2.56])
def test_the_rate_and_the_time_it_buys_are_two_readings_of_one_number(seconds: float) -> None:
    fadeout = fadeout_value(seconds, counter=COUNTER, tempo=TEMPO)
    assert fade_seconds(fadeout, counter=COUNTER, tempo=TEMPO) == pytest.approx(seconds)


def test_a_fade_of_no_time_is_refused() -> None:
    with pytest.raises(ValueError):
        fadeout_value(0.0, counter=COUNTER, tempo=TEMPO)


def test_a_fade_slower_than_the_counter_reaches_is_refused() -> None:
    # Rounding down would give the value that means no fade at all, which is the opposite of a slow one.
    longest = fade_seconds(1, counter=COUNTER, tempo=TEMPO)
    assert fadeout_value(longest, counter=COUNTER, tempo=TEMPO) == 1
    with pytest.raises(ValueError):
        fadeout_value(2 * longest, counter=COUNTER, tempo=TEMPO)


def test_impulse_tracker_counts_down_from_its_own_counter() -> None:
    assert it_fade.fade_ticks(IT_MAX_FADEOUT) == pytest.approx(FASTEST_CANONICAL_TICKS)
    assert it_fade.fade_seconds(32, tempo=TEMPO) == pytest.approx(IT_COUNTER / 32 * tick_seconds(TEMPO))
    assert it_fade.fadeout_value(0.64, tempo=TEMPO) == 32


def test_fast_tracker_counts_down_from_a_counter_thirty_two_times_as_wide() -> None:
    assert xm_fade.fade_ticks(XM_MAX_FADEOUT) == pytest.approx(FASTEST_CANONICAL_TICKS, abs=0.01)
    assert xm_fade.fade_seconds(1024, tempo=TEMPO) == pytest.approx(XM_COUNTER / 1024 * tick_seconds(TEMPO))
    assert xm_fade.fadeout_value(0.64, tempo=TEMPO) == 1024


def test_the_two_formats_reach_the_same_fade_through_different_numbers() -> None:
    """One counter is 32 times the other, so the same fade is stated 32 times larger in one of them."""
    assert XM_COUNTER == 32 * IT_COUNTER
    seconds = 0.64
    assert xm_fade.fadeout_value(seconds, tempo=TEMPO) == 32 * it_fade.fadeout_value(seconds, tempo=TEMPO)
    assert xm_fade.fade_seconds(1024, tempo=TEMPO) == pytest.approx(it_fade.fade_seconds(32, tempo=TEMPO))

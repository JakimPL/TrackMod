import pytest

from trackmod.core.timing.clock import elapsed_ticks, row_seconds, tick_seconds
from trackmod.core.timing.lattice import row_frames
from trackmod.limits.bound import Bound

FRAME_RATE = 44100
SPEED = Bound(minimum=1, maximum=255)
TEMPO = Bound(minimum=32, maximum=255)


@pytest.mark.parametrize(
    ("tempo", "seconds"),
    [(125, 0.020), (150, 1 / 60), (250, 0.010), (50, 0.050)],
)
def test_a_tick_lasts_five_halves_of_the_tempo(tempo: int, seconds: float) -> None:
    assert tick_seconds(tempo) == pytest.approx(seconds)


def test_a_row_is_as_many_ticks_as_the_speed_names() -> None:
    assert row_seconds(6, 125) == pytest.approx(6 * tick_seconds(125))


def test_the_clock_in_seconds_agrees_with_the_clock_in_frames() -> None:
    # The two say the same thing in different units, so a row measured either way spans the same time.
    frames = row_frames(6, 125, frame_rate=FRAME_RATE, speed_bound=SPEED, tempo_bound=TEMPO)
    assert frames / FRAME_RATE == pytest.approx(row_seconds(6, 125))


@pytest.mark.parametrize(("seconds", "ticks"), [(0.0, 0), (0.02, 1), (0.029, 1), (0.031, 2), (1.0, 50)])
def test_a_duration_lands_on_the_nearest_whole_tick(seconds: float, ticks: int) -> None:
    assert elapsed_ticks(seconds, 125) == ticks


def test_a_stopped_clock_is_refused() -> None:
    with pytest.raises(ValueError):
        tick_seconds(0)


def test_a_row_of_no_ticks_is_refused() -> None:
    with pytest.raises(ValueError):
        row_seconds(0, 125)


def test_a_duration_running_backwards_is_refused() -> None:
    with pytest.raises(ValueError):
        elapsed_ticks(-0.5, 125)

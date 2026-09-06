from dataclasses import dataclass

import pytest

from trackmod.core.timing.lattice import exact_timings, nearest_timing, row_frames
from trackmod.limits.bound import Bound
from trackmod.utils.arithmetic import neighbor_divisors

FRAME_RATE = 44100
SPEED = Bound(minimum=1, maximum=255)
NARROW_TEMPO = Bound(minimum=32, maximum=255)
WIDE_TEMPO = Bound(minimum=32, maximum=65535)


@dataclass(frozen=True)
class LatticePoint:
    tempo: int
    frames: int


LATTICE = (
    LatticePoint(tempo=75, frames=1470),
    LatticePoint(tempo=125, frames=882),
    LatticePoint(tempo=150, frames=735),
    LatticePoint(tempo=250, frames=441),
    LatticePoint(tempo=441, frames=250),
    LatticePoint(tempo=2205, frames=50),
    LatticePoint(tempo=11025, frames=10),
)


@pytest.mark.parametrize("point", LATTICE, ids=lambda point: f"tempo{point.tempo}")
def test_row_frames_hits_the_whole_frame_lattice(point: LatticePoint) -> None:
    assert row_frames(1, point.tempo, frame_rate=FRAME_RATE, speed_bound=SPEED, tempo_bound=WIDE_TEMPO) == point.frames


def test_a_fractional_row_is_refused() -> None:
    with pytest.raises(ValueError):
        row_frames(1, 187, frame_rate=FRAME_RATE, speed_bound=SPEED, tempo_bound=WIDE_TEMPO)


def test_tempo_outside_its_bound_is_refused() -> None:
    with pytest.raises(ValueError):
        row_frames(1, 441, frame_rate=FRAME_RATE, speed_bound=SPEED, tempo_bound=NARROW_TEMPO)


def test_speed_is_bounded_by_its_own_range_not_the_tempo_range() -> None:
    # The speed guard has its own bound: a speed beyond it fails even where the tempo range is far wider.
    with pytest.raises(ValueError):
        row_frames(256, 125, frame_rate=FRAME_RATE, speed_bound=SPEED, tempo_bound=WIDE_TEMPO)

    assert row_frames(2, 125, frame_rate=FRAME_RATE, speed_bound=SPEED, tempo_bound=WIDE_TEMPO) == 1764


def test_exact_timings_are_whole_frames_and_sorted() -> None:
    timings = exact_timings(frame_rate=FRAME_RATE, speed=1, speed_bound=SPEED, tempo_bound=NARROW_TEMPO)
    lengths = [timing.row_frames for timing in timings]
    assert lengths == sorted(lengths)
    for timing in timings:
        assert timing.row_frames * 2 * timing.tempo == timing.speed * FRAME_RATE * 5


def test_the_wide_tempo_bound_reaches_rows_the_narrow_one_cannot() -> None:
    narrow = exact_timings(frame_rate=FRAME_RATE, speed=1, speed_bound=SPEED, tempo_bound=NARROW_TEMPO)
    wide = exact_timings(frame_rate=FRAME_RATE, speed=1, speed_bound=SPEED, tempo_bound=WIDE_TEMPO)
    assert wide[0].row_frames < narrow[0].row_frames


def test_nearest_timing_prefers_an_exact_match() -> None:
    timing = nearest_timing(882, frame_rate=FRAME_RATE, speed=1, speed_bound=SPEED, tempo_bound=NARROW_TEMPO)
    assert timing.row_frames == 882
    assert timing.tempo == 125


def test_nearest_timing_resolves_ties_to_the_shorter_row() -> None:
    # 450 and 490 frames both sit 20 frames from 470, so the tie-break decides; the shorter row wins.
    timing = nearest_timing(470, frame_rate=FRAME_RATE, speed=1, speed_bound=SPEED, tempo_bound=NARROW_TEMPO)
    assert timing.row_frames == 450


def test_nearest_timing_picks_the_closest_row_when_there_is_no_tie() -> None:
    timing = nearest_timing(588, frame_rate=FRAME_RATE, speed=1, speed_bound=SPEED, tempo_bound=NARROW_TEMPO)
    assert timing.row_frames == 630


@pytest.mark.parametrize("candidate", [0, -1, 13])
def test_a_candidate_outside_the_dividend_is_refused(candidate: int) -> None:
    # The two neighbours are divisors of the dividend, so a candidate outside it has no side to fall on.
    with pytest.raises(ValueError, match="must be in 1..12"):
        neighbor_divisors(candidate, 12)


def test_a_candidate_that_divides_is_its_own_neighbour_on_both_sides() -> None:
    assert neighbor_divisors(4, 12) == (4, 4)


def test_a_candidate_between_two_divisors_is_answered_by_both() -> None:
    assert neighbor_divisors(5, 12) == (4, 6)

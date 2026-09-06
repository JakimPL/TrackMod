from trackmod.trackers.s3m.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.s3m.spec.ranges import MAX_SPEED, MAX_TEMPO, MIN_TEMPO
from trackmod.trackers.s3m.timing import TIMINGS

FRAME_RATE = 44100


def test_the_clock_a_module_starts_on_lasts_the_length_the_lineage_reads() -> None:
    assert TIMINGS.row_frames(DEFAULT_SPEED, DEFAULT_TEMPO, frame_rate=FRAME_RATE) == round(FRAME_RATE * 6 * 0.02)


def test_the_lattice_reaches_as_far_as_the_two_bytes_the_header_states_it_in() -> None:
    timings = TIMINGS.exact_timings(frame_rate=FRAME_RATE, speed=DEFAULT_SPEED)
    assert timings
    assert all(MIN_TEMPO <= timing.tempo <= MAX_TEMPO for timing in timings)
    assert all(timing.speed == DEFAULT_SPEED for timing in timings)


def test_a_target_row_length_lands_on_the_nearest_clock_the_format_reaches() -> None:
    target = TIMINGS.row_frames(DEFAULT_SPEED, 140, frame_rate=FRAME_RATE)
    assert TIMINGS.nearest_timing(target, frame_rate=FRAME_RATE, speed=DEFAULT_SPEED).tempo == 140


def test_a_speed_the_header_reaches_lengthens_the_row_it_states() -> None:
    slow = TIMINGS.row_frames(MAX_SPEED, DEFAULT_TEMPO, frame_rate=FRAME_RATE)
    quick = TIMINGS.row_frames(1, DEFAULT_TEMPO, frame_rate=FRAME_RATE)
    assert quick * MAX_SPEED == slow

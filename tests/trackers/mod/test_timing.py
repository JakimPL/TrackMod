from trackmod.trackers.mod.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.mod.spec.ranges import MAX_EFFECT_SPEED, MAX_EFFECT_TEMPO, MIN_EFFECT_TEMPO
from trackmod.trackers.mod.timing import TIMINGS

FRAME_RATE = 44100


def test_the_clock_a_module_starts_on_lasts_the_length_the_lineage_reads() -> None:
    # Six ticks at 125 beats a minute is a row of twenty milliseconds a tick, which is what every module
    # of this format starts at and what its header leaves unstated.
    assert TIMINGS.row_frames(DEFAULT_SPEED, DEFAULT_TEMPO, frame_rate=FRAME_RATE) == round(FRAME_RATE * 6 * 0.02)


def test_the_lattice_reaches_no_further_than_the_one_command_that_states_it() -> None:
    # The header carries no clock, so what a module can time to is exactly what its effect parameter
    # holds: one byte, split between the ticks a row lasts and the beats a minute.
    timings = TIMINGS.exact_timings(frame_rate=FRAME_RATE, speed=DEFAULT_SPEED)
    assert timings
    assert all(MIN_EFFECT_TEMPO <= timing.tempo <= MAX_EFFECT_TEMPO for timing in timings)
    assert all(timing.speed == DEFAULT_SPEED for timing in timings)


def test_a_target_row_length_lands_on_the_nearest_clock_the_format_reaches() -> None:
    target = TIMINGS.row_frames(DEFAULT_SPEED, 140, frame_rate=FRAME_RATE)
    assert TIMINGS.nearest_timing(target, frame_rate=FRAME_RATE, speed=DEFAULT_SPEED).tempo == 140


def test_a_speed_the_command_reaches_shortens_the_row_it_states() -> None:
    slow = TIMINGS.row_frames(MAX_EFFECT_SPEED, DEFAULT_TEMPO, frame_rate=FRAME_RATE)
    quick = TIMINGS.row_frames(1, DEFAULT_TEMPO, frame_rate=FRAME_RATE)
    assert quick * MAX_EFFECT_SPEED == slow

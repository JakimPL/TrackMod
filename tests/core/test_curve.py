import pytest

from trackmod.core.envelopes.curve import (
    Breakpoint,
    envelope_seconds,
    placed_ticks,
    timed_envelope,
)
from trackmod.core.envelopes.span import EnvelopeSpan
from trackmod.core.timing.clock import tick_seconds
from trackmod.limits.bound import Bound

TEMPO = 125
TICKS = Bound(minimum=0, maximum=65535)
VOLUME = Bound(minimum=0, maximum=64)

DECAY = (
    Breakpoint(seconds=0.0, value=64),
    Breakpoint(seconds=0.5, value=64),
    Breakpoint(seconds=3.0, value=16),
    Breakpoint(seconds=3.25, value=0),
)


def curve(breakpoints: tuple[Breakpoint, ...] = DECAY, *, ticks: Bound = TICKS):
    return timed_envelope(breakpoints, tempo=TEMPO, tick_bound=ticks, value_bound=VOLUME)


def test_a_breakpoint_lands_on_the_tick_its_time_falls_on() -> None:
    assert [point.tick for point in curve().points] == [0, 25, 150, 162]


def test_the_values_are_carried_across_as_stated() -> None:
    assert [point.value for point in curve().points] == [64, 64, 16, 0]


def test_a_value_the_grid_stops_short_of_is_written_at_the_nearest_step() -> None:
    loud = (Breakpoint(seconds=0.0, value=200), Breakpoint(seconds=1.0, value=-30))
    assert [point.value for point in curve(loud).points] == [64, 0]


def test_two_breakpoints_inside_one_tick_are_moved_apart() -> None:
    # A format orders its breakpoints by tick, so a curve settling faster than the clock still names both ends.
    instant = (Breakpoint(seconds=0.0, value=64), Breakpoint(seconds=0.0001, value=32))
    assert [point.tick for point in curve(instant).points] == [0, 1]


def test_a_curve_running_past_the_last_tick_keeps_every_breakpoint() -> None:
    narrow = Bound(minimum=0, maximum=3)
    assert [point.tick for point in curve(ticks=narrow).points] == [0, 1, 2, 3]


def test_more_breakpoints_than_there_are_ticks_is_refused() -> None:
    with pytest.raises(ValueError):
        curve(ticks=Bound(minimum=0, maximum=2))


def test_the_ticks_start_where_the_bound_does() -> None:
    shifted = placed_ticks(DECAY, tempo=TEMPO, bound=Bound(minimum=10, maximum=65535))
    assert shifted[0] == 10


def test_the_spans_are_carried_over_the_breakpoints_as_given() -> None:
    held = EnvelopeSpan(begin=2, end=2)
    envelope = timed_envelope(DECAY, tempo=TEMPO, tick_bound=TICKS, value_bound=VOLUME, sustain=held)
    assert envelope.sustain == held
    assert envelope.loop is None


def test_a_curve_read_back_states_the_times_it_was_written_from() -> None:
    read = envelope_seconds(curve(), tempo=TEMPO)
    assert [point.seconds for point in read] == pytest.approx([0.0, 0.5, 3.0, 3.24])
    assert [point.value for point in read] == [64, 64, 16, 0]


def test_the_same_curve_at_a_faster_tempo_lands_on_later_ticks() -> None:
    # Ticks are the unit, so halving a tick's length doubles how many of them a fixed span covers.
    quick = timed_envelope(DECAY, tempo=2 * TEMPO, tick_bound=TICKS, value_bound=VOLUME)
    assert tick_seconds(2 * TEMPO) == pytest.approx(tick_seconds(TEMPO) / 2)
    assert [point.tick for point in quick.points] == [0, 50, 300, 325]

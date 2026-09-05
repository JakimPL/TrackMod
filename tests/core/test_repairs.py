import warnings

import pytest

from trackmod.core.envelopes.point import EnvelopePoint
from trackmod.core.envelopes.repair import repaired_points, repaired_span
from trackmod.core.envelopes.span import EnvelopeSpan
from trackmod.core.instruments.behaviour import DuplicateAction
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.keymap import KeyAssignment, pitched_keymap, routed_keymap
from trackmod.core.instruments.repair import routed_within, stated_behaviour
from trackmod.core.notes.pitch import Note
from trackmod.core.repairs.report import Repairs, RepairWarning
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.repair import repaired_loop, repaired_rate
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.repair import repaired_order
from trackmod.spec.pitch import REFERENCE_RATE

SUBJECT = "sample 3"


def test_a_parse_that_repairs_nothing_warns_about_nothing() -> None:
    repairs = Repairs()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        repairs.warn()

    assert repairs.entries == ()
    assert caught == []


def test_one_warning_covers_every_repair_a_parse_made() -> None:
    repairs = Repairs()
    repairs.made("drawn in", subject="sample 0")
    repairs.made("drawn in", subject="sample 0")
    repairs.made("held back", subject="sample 1")
    with pytest.warns(RepairWarning, match="drawn in.*held back"):
        repairs.warn()

    assert repairs.entries == (("sample 0", "drawn in"), ("sample 1", "held back"))


def test_an_envelope_span_past_the_points_is_drawn_onto_the_last_one() -> None:
    repairs = Repairs()
    span = repaired_span((1, 9), points=4, name="volume loop", subject=SUBJECT, repairs=repairs)
    assert span == EnvelopeSpan(begin=1, end=3)
    assert repairs.entries == ((SUBJECT, "volume loop span 1..9 drawn to 1..3"),)


def test_an_envelope_span_ending_before_it_begins_closes_onto_its_end() -> None:
    # The pair is taken as the two numbers the record holds: a span that runs backwards is one this
    # model states no span for, so it can only be read from the raw bytes.
    repairs = Repairs()
    assert repaired_span((5, 2), points=8, name="loop", subject=SUBJECT, repairs=repairs) == EnvelopeSpan(
        begin=2, end=2
    )
    assert repaired_span((3, 3), points=2, name="loop", subject=SUBJECT, repairs=repairs) == EnvelopeSpan(
        begin=1, end=1
    )


def test_a_span_already_inside_the_points_is_left_as_it_is() -> None:
    repairs = Repairs()
    assert repaired_span((0, 2), points=4, name="loop", subject=SUBJECT, repairs=repairs) == EnvelopeSpan(
        begin=0, end=2
    )
    assert repairs.entries == ()


def test_envelope_points_stated_out_of_order_are_held_at_the_tick_before_them() -> None:
    repairs = Repairs()
    points = repaired_points(
        [EnvelopePoint(tick=0, value=64), EnvelopePoint(tick=9, value=32), EnvelopePoint(tick=4, value=0)],
        subject=SUBJECT,
        repairs=repairs,
    )
    assert [point.tick for point in points] == [0, 9, 9]
    assert [point.value for point in points] == [64, 32, 0]
    assert repairs.entries == ((SUBJECT, "1 envelope points stated out of order held at the tick before them"),)


def test_points_sharing_a_tick_are_left_as_they_are() -> None:
    repairs = Repairs()
    stated = [EnvelopePoint(tick=0, value=64), EnvelopePoint(tick=0, value=0)]
    assert repaired_points(stated, subject=SUBJECT, repairs=repairs) == tuple(stated)
    assert repairs.entries == ()


def test_a_loop_past_the_frames_stored_is_drawn_back_onto_them() -> None:
    repairs = Repairs()
    loop = repaired_loop(
        Loop(begin=4, end=900, mode=LoopMode.PING_PONG), frames=64, name="loop", subject=SUBJECT, repairs=repairs
    )
    assert loop == Loop(begin=4, end=64, mode=LoopMode.PING_PONG)
    assert repairs.entries == ((SUBJECT, "loop 4..900 drawn to 4..64 of 64 frames"),)


def test_a_loop_left_with_nothing_between_its_ends_repeats_nothing() -> None:
    repairs = Repairs()
    assert repaired_loop(Loop(begin=80, end=90), frames=8, name="loop", subject=SUBJECT, repairs=repairs) is None


def test_a_rate_of_zero_is_read_as_the_reference_rate() -> None:
    repairs = Repairs()
    assert repaired_rate(0, subject=SUBJECT, repairs=repairs) == REFERENCE_RATE
    assert repaired_rate(44100, subject=SUBJECT, repairs=repairs) == 44100
    assert len(repairs.entries) == 1


def test_order_positions_naming_no_stored_pattern_are_dropped() -> None:
    repairs = Repairs()
    order = repaired_order(OrderList(entries=(0, 7, 1, 9), restart=3), patterns=2, subject="song", repairs=repairs)
    assert order.entries == (0, 1)
    assert order.restart == 1
    assert repairs.entries == (("song", "2 order positions naming no stored pattern dropped"),)


def test_an_order_list_naming_only_stored_patterns_is_left_as_it_is() -> None:
    repairs = Repairs()
    order = OrderList(entries=(0, 1, 0))
    assert repaired_order(order, patterns=2, subject="song", repairs=repairs) is order


def test_keys_routed_past_the_samples_stored_are_left_silent() -> None:
    repairs = Repairs()
    instrument = Instrument(
        name="lead",
        keymap=routed_keymap(
            {Note(60): KeyAssignment(sample=0, note=Note(60)), Note(62): KeyAssignment(sample=5, note=Note(62))}
        ),
    )
    routed = routed_within(instrument, samples=2, subject="instrument 0", repairs=repairs)
    assert routed.samples == (0,)
    assert routed.assignment(Note(62)) is None
    assert repairs.entries == (("instrument 0", "1 keys routed past the 2 samples stored are left silent"),)


def test_an_instrument_reaching_only_stored_samples_is_left_as_it_is() -> None:
    repairs = Repairs()
    instrument = Instrument(name="lead", keymap=pitched_keymap(sample=0))
    assert routed_within(instrument, samples=1, subject="instrument 0", repairs=repairs) is instrument
    assert repairs.entries == ()


def test_a_behaviour_byte_naming_none_of_them_is_read_as_the_one_a_fresh_instrument_carries() -> None:
    repairs = Repairs()
    action = stated_behaviour(
        200,
        among=DuplicateAction,
        default=DuplicateAction.CUT,
        name="duplicate action",
        subject="instrument 0",
        repairs=repairs,
    )
    assert action is DuplicateAction.CUT
    assert repairs.entries == (("instrument 0", "duplicate action 200 read as CUT"),)


def test_a_behaviour_byte_the_format_numbers_is_read_as_that_behaviour() -> None:
    repairs = Repairs()
    action = stated_behaviour(
        int(DuplicateAction.FADE),
        among=DuplicateAction,
        default=DuplicateAction.CUT,
        name="duplicate action",
        subject="instrument 0",
        repairs=repairs,
    )
    assert action is DuplicateAction.FADE
    assert repairs.entries == ()

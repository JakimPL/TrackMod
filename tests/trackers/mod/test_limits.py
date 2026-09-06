import pytest

from tests.conftest import rescaled
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.grid import Pattern
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.song import Song
from trackmod.limits.capability import Capability
from trackmod.limits.compliance import Compliance
from trackmod.spec.pitch import REFERENCE_RATE
from trackmod.trackers.mod.limits import mod_limits
from trackmod.trackers.mod.module import MODModule
from trackmod.trackers.mod.spec.identity import TAG_BYTES, TAG_OFFSET
from trackmod.trackers.mod.spec.periods import (
    CANONICAL_MAX_NOTE,
    CANONICAL_MIN_NOTE,
    MAX_NOTE,
    MIN_NOTE,
)
from trackmod.trackers.mod.spec.ranges import (
    CANONICAL_CHANNELS,
    EXTENDED_MAX_CHANNELS,
    EXTENDED_MAX_PATTERNS,
    MAX_SAMPLE_RATE,
    MAX_SAMPLES,
    MIN_SAMPLE_RATE,
    PATTERN_ROWS,
    STRUCTURAL_MAX_CHANNELS,
    TAGGED_MAX_PATTERNS,
)

PINNED = (Capability.SPEED, Capability.TEMPO, Capability.PATTERN_ROWS, Capability.SAMPLE_GAIN)
WIDE_CHANNELS = 40
WIDE_TAG = b"40CH"


def test_the_width_the_tracker_read_is_the_only_canonical_one() -> None:
    canonical = mod_limits(Compliance.CANONICAL).bound(Capability.CHANNELS)
    extended = mod_limits(Compliance.EXTENDED).bound(Capability.CHANNELS)
    structural = mod_limits(Compliance.STRUCTURAL).bound(Capability.CHANNELS)
    assert canonical.minimum == canonical.maximum == CANONICAL_CHANNELS
    assert (extended.maximum, structural.maximum) == (EXTENDED_MAX_CHANNELS, STRUCTURAL_MAX_CHANNELS)
    assert (extended.maximum, structural.maximum) == (32, 99)


def test_a_width_the_tag_spells_but_the_players_stop_short_of_is_stored_and_reported(mod_song: Song) -> None:
    # Two digits and the letters naming them fill the tag, so the families spell a width the players
    # descended from this format read no module at -- which is what makes the two levels part company.
    module = MODModule.from_song(rescaled(mod_song, WIDE_CHANNELS), compliance=Compliance.STRUCTURAL)
    assert module.violations() == ()

    (reported,) = module.exceeded()
    assert reported.capability is Capability.CHANNELS
    assert reported.level is Compliance.EXTENDED

    data = module.to_bytes()
    assert data[TAG_OFFSET : TAG_OFFSET + TAG_BYTES] == WIDE_TAG
    assert MODModule.parse(data).song.channels == WIDE_CHANNELS


def test_more_patterns_than_the_plain_tag_was_read_with_reaches_past_the_tracker(mod_song: Song) -> None:
    many = mod_song.model_copy(
        update={
            "patterns": tuple(mod_song.patterns[0] for _ in range(TAGGED_MAX_PATTERNS + 1)),
            "order": OrderList(entries=(0,)),
        }
    )
    assert MODModule.from_song(many, compliance=Compliance.EXTENDED).violations() == ()

    (reported,) = MODModule.from_song(many, compliance=Compliance.CANONICAL).violations()
    assert reported.capability is Capability.PATTERNS
    assert reported.level is Compliance.CANONICAL


def test_a_pinned_capacity_states_one_value_at_either_level() -> None:
    # A pinned bound is how this format says it applies no such adjustment: the header states no clock
    # and every pattern is the same height, so a song asking for another is told rather than losing it.
    for compliance in Compliance:
        limits = mod_limits(compliance)
        for capability in PINNED:
            bound = limits.bound(capability)
            assert bound.minimum == bound.maximum


def test_the_key_range_is_bounded_at_both_ends() -> None:
    canonical = mod_limits(Compliance.CANONICAL).bound(Capability.NOTE)
    extended = mod_limits(Compliance.EXTENDED).bound(Capability.NOTE)
    assert (canonical.minimum, canonical.maximum) == (CANONICAL_MIN_NOTE, CANONICAL_MAX_NOTE)
    assert (extended.minimum, extended.maximum) == (MIN_NOTE, MAX_NOTE)


def test_a_key_below_the_tabulated_octaves_is_reported_rather_than_refused(mod_song: Song) -> None:
    # The tabulated keyboard has a floor as well as a ceiling, so the deepest key a pattern plays is
    # graded beside the highest -- a pattern climbing no higher than the table reaches can still open
    # below where it starts.
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=CANONICAL_CHANNELS)
    builder.place(0, 0, Cell(note=Note(CANONICAL_MIN_NOTE - 1), instrument=0))
    builder.place(1, 0, Cell(note=Note(CANONICAL_MAX_NOTE), instrument=0))
    low = mod_song.model_copy(
        update={"patterns": (builder.build(),), "order": mod_song.order.model_copy(update={"entries": (0,)})}
    )

    assert MODModule.from_song(low, compliance=Compliance.EXTENDED).violations() == ()
    (reported,) = MODModule.from_song(low, compliance=Compliance.CANONICAL).violations()
    assert reported.capability is Capability.NOTE
    assert reported.value == CANONICAL_MIN_NOTE - 1
    assert reported.level is Compliance.CANONICAL


def test_a_pattern_playing_no_key_reports_nothing_about_keys(mod_song: Song) -> None:
    silent = mod_song.model_copy(
        update={
            "patterns": (Pattern.empty(rows=PATTERN_ROWS, channels=CANONICAL_CHANNELS),),
            "order": mod_song.order.model_copy(update={"entries": (0,), "restart": 0}),
        }
    )
    assert MODModule.from_song(silent, compliance=Compliance.CANONICAL).violations() == ()


def test_the_rate_bound_is_the_sixteen_rows_the_tuning_reaches() -> None:
    bound = mod_limits(Compliance.EXTENDED).bound(Capability.SAMPLE_RATE)
    assert (bound.minimum, bound.maximum) == (MIN_SAMPLE_RATE, MAX_SAMPLE_RATE)
    assert bound.contains(REFERENCE_RATE)
    assert not bound.contains(44100)


def test_the_slots_a_module_holds_are_the_records_it_writes() -> None:
    assert mod_limits(Compliance.EXTENDED).bound(Capability.SAMPLES).maximum == MAX_SAMPLES


def test_the_order_byte_is_what_lets_a_module_reach_its_widest_pattern_table() -> None:
    # Nothing in the table is reserved, so an order names any byte and the count it reaches is the byte
    # range itself — which is further than the tracker's own editor ever went.
    canonical = mod_limits(Compliance.CANONICAL).bound(Capability.PATTERNS)
    extended = mod_limits(Compliance.EXTENDED).bound(Capability.PATTERNS)
    assert extended.maximum == EXTENDED_MAX_PATTERNS
    assert canonical.maximum < extended.maximum


def test_a_field_this_format_has_no_room_for_states_no_capacity() -> None:
    limits = mod_limits(Compliance.EXTENDED)
    for capability in (Capability.FADEOUT, Capability.VOLUME_COMMAND, Capability.INSTRUMENTS):
        with pytest.raises(ValueError, match=f"keeps no field for {capability.value}"):
            limits.bound(capability)

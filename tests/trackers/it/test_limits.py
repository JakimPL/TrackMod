import pytest

from tests.conftest import GridShape, random_pattern, rescaled
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.song import Song
from trackmod.core.volumes.command import VolumeCommand, VolumeEffect
from trackmod.limits.capability import Capability
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import LimitError
from trackmod.limits.severity import Severity
from trackmod.spec.width import BYTE_MAX, WORD_MAX
from trackmod.trackers.it.limits import it_limits
from trackmod.trackers.it.module import ITModule
from trackmod.trackers.it.spec.ranges import (
    CANONICAL_MAX_CHANNELS,
    CANONICAL_MAX_FADEOUT,
    EXTENDED_MAX_CHANNELS,
    MAX_ROWS,
    MAX_VOLUME_COMMAND,
    MAX_VOLUME_PANNING,
)


@pytest.mark.parametrize("compliance", list(Compliance))
def test_this_format_has_no_headroom_above_its_one_byte_tempo(compliance: Compliance) -> None:
    # The header stores the tempo in a single byte, so no compliance level reaches past it.
    assert it_limits(compliance).bound(Capability.TEMPO).maximum == BYTE_MAX


def test_the_channel_count_is_the_one_capability_with_headroom() -> None:
    canonical = it_limits(Compliance.CANONICAL).bound(Capability.CHANNELS)
    extended = it_limits(Compliance.EXTENDED).bound(Capability.CHANNELS)
    assert canonical.maximum == CANONICAL_MAX_CHANNELS
    assert extended.maximum == EXTENDED_MAX_CHANNELS


def test_the_fadeout_the_tracker_honours_stops_short_of_what_its_field_holds() -> None:
    # The header keeps a word, and Impulse Tracker's own editor counts a fadeout up to 128.
    assert it_limits(Compliance.CANONICAL).bound(Capability.FADEOUT).maximum == CANONICAL_MAX_FADEOUT
    assert it_limits(Compliance.EXTENDED).bound(Capability.FADEOUT).maximum == WORD_MAX


def test_a_fadeout_past_the_tracker_is_a_compliance_violation_the_extended_level_allows(song: Song) -> None:
    faster = song.instruments[0].model_copy(update={"fadeout": 2 * CANONICAL_MAX_FADEOUT})
    quick = song.model_copy(update={"instruments": (faster, *song.instruments[1:])})
    canonical = ITModule.from_song(quick, compliance=Compliance.CANONICAL).violations()
    assert [violation.capability for violation in canonical] == [Capability.FADEOUT]
    assert canonical[0].severity is Severity.COMPLIANCE
    assert ITModule.from_song(quick, compliance=Compliance.EXTENDED).violations() == ()


def test_extra_channels_are_a_compliance_violation_the_extended_level_allows(song: Song) -> None:
    wide = rescaled(song, 96)
    canonical = ITModule.from_song(wide, compliance=Compliance.CANONICAL).violations()
    assert [violation.capability for violation in canonical] == [Capability.CHANNELS]
    assert canonical[0].severity is Severity.COMPLIANCE
    assert ITModule.from_song(wide, compliance=Compliance.EXTENDED).violations() == ()


def test_writing_a_module_the_format_refuses_raises(song: Song) -> None:
    over = rescaled(song, 200)
    with pytest.raises(LimitError) as error:
        ITModule.from_song(over, compliance=Compliance.EXTENDED).to_bytes()

    assert error.value.violations[0].severity is Severity.STRUCTURAL


def test_a_short_pattern_is_a_compliance_violation_the_extended_level_allows(song: Song) -> None:
    short = Song(
        name=song.name,
        channels=song.channels,
        patterns=(random_pattern(GridShape(rows=8, channels=song.channels, instruments=2, seed=5)),),
        order=OrderList(entries=(0,)),
        instruments=song.instruments,
        samples=song.samples,
        playback=song.playback,
    )
    canonical = ITModule.from_song(short, compliance=Compliance.CANONICAL).violations()
    assert [violation.capability for violation in canonical] == [Capability.PATTERN_ROWS]
    assert ITModule.from_song(short, compliance=Compliance.EXTENDED).violations() == ()


def test_a_pattern_over_the_size_field_is_reported(song: Song) -> None:
    crowded = random_pattern(GridShape(rows=MAX_ROWS, channels=127, instruments=8, seed=99))
    wide = Song(
        name=song.name,
        channels=127,
        patterns=(crowded,),
        order=OrderList(entries=(0,)),
        instruments=song.instruments,
        samples=song.samples,
        playback=song.playback,
    )
    reported = [
        violation.capability for violation in ITModule.from_song(wide, compliance=Compliance.EXTENDED).violations()
    ]
    assert Capability.PATTERN_BYTES in reported


PATTERN_ROWS = 32
SPARE_EFFECT = VolumeEffect.VIBRATO_DEPTH
UNNAMED_EFFECT = VolumeEffect.VIBRATO_SPEED


def volumed(song: Song, volume: VolumeCommand) -> Song:
    """The song with one pattern stating ``volume``, which is what a volume-column bound is graded over."""
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=song.channels)
    builder.place(0, 0, Cell(note=Note(60), instrument=0, volume=volume))
    return song.model_copy(update={"patterns": (builder.build(),), "order": OrderList.sequential(1)})


def test_the_amounts_a_volume_column_holds_are_bounded_apart_from_its_panning() -> None:
    limits = it_limits(Compliance.CANONICAL)
    assert limits.bound(Capability.VOLUME_COMMAND).maximum == MAX_VOLUME_COMMAND
    assert limits.bound(Capability.VOLUME_PANNING).maximum == MAX_VOLUME_PANNING


def test_an_amount_past_what_the_column_holds_is_reported(song: Song) -> None:
    past = volumed(song, VolumeCommand(effect=VolumeEffect.VOLUME_SLIDE_UP, amount=MAX_VOLUME_COMMAND + 1))
    (violation,) = ITModule.from_song(past, compliance=Compliance.EXTENDED).violations()
    assert violation.capability is Capability.VOLUME_COMMAND
    assert violation.value == MAX_VOLUME_COMMAND + 1
    assert violation.severity is Severity.STRUCTURAL
    assert violation.subject == "pattern 0"


def test_a_panning_position_is_graded_on_its_own_field(song: Song) -> None:
    # Panning counts a different number of steps from the rates, so the two are bounded apart.
    held = volumed(song, VolumeCommand(effect=VolumeEffect.PANNING, amount=MAX_VOLUME_PANNING))
    assert ITModule.from_song(held, compliance=Compliance.EXTENDED).violations() == ()

    past = volumed(song, VolumeCommand(effect=VolumeEffect.PANNING, amount=MAX_VOLUME_PANNING + 1))
    (violation,) = ITModule.from_song(past, compliance=Compliance.EXTENDED).violations()
    assert violation.capability is Capability.VOLUME_PANNING


def test_a_pattern_states_one_violation_per_quantity_however_many_cells_carry_one(song: Song) -> None:
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=song.channels)
    for row, amount in enumerate((MAX_VOLUME_COMMAND + 1, MAX_VOLUME_COMMAND + 3, MAX_VOLUME_COMMAND + 2)):
        builder.place(row, 0, Cell(note=Note(60), volume=VolumeCommand(effect=SPARE_EFFECT, amount=amount)))

    crowded = song.model_copy(update={"patterns": (builder.build(),), "order": OrderList.sequential(1)})
    (violation,) = ITModule.from_song(crowded, compliance=Compliance.EXTENDED).violations()
    assert violation.value == MAX_VOLUME_COMMAND + 3


def test_an_effect_this_column_has_no_run_for_raises_where_it_is_met(song: Song) -> None:
    # A bound says use a smaller number; content the column cannot state at all has no bound to report.
    unnamed = volumed(song, VolumeCommand(effect=UNNAMED_EFFECT, amount=0))
    module = ITModule.from_song(unnamed, compliance=Compliance.EXTENDED)
    assert module.violations() == ()
    with pytest.raises(ValueError, match="no run for"):
        module.to_bytes()

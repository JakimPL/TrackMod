import pytest

from tests.conftest import rescaled, revoiced
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import InstrumentVoices
from trackmod.core.volumes.command import VolumeCommand, VolumeEffect
from trackmod.limits.capability import Capability
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import LimitError
from trackmod.limits.severity import Severity
from trackmod.spec.levels import MAX_VOLUME
from trackmod.spec.width import WORD_MAX
from trackmod.trackers.xm.limits import xm_limits
from trackmod.trackers.xm.module import XMModule
from trackmod.trackers.xm.spec.ranges import (
    CANONICAL_MAX_CHANNELS,
    CANONICAL_MAX_FADEOUT,
    CANONICAL_MAX_TEMPO,
    EXTENDED_MAX_CHANNELS,
    MAX_NOTE,
    MAX_VOLUME_COMMAND,
    MAX_VOLUME_PANNING,
)


def test_the_tempo_word_is_where_this_format_has_its_headroom() -> None:
    # The header stores the tempo in sixteen bits while the tracker honours one byte of it, which is
    # the whole reason a caller reaching for a shorter row chooses this format.
    assert xm_limits(Compliance.CANONICAL).bound(Capability.TEMPO).maximum == CANONICAL_MAX_TEMPO
    assert xm_limits(Compliance.EXTENDED).bound(Capability.TEMPO).maximum == WORD_MAX


def test_the_channel_count_has_headroom_too() -> None:
    assert xm_limits(Compliance.CANONICAL).bound(Capability.CHANNELS).maximum == CANONICAL_MAX_CHANNELS
    assert xm_limits(Compliance.EXTENDED).bound(Capability.CHANNELS).maximum == EXTENDED_MAX_CHANNELS


def test_the_fadeout_the_tracker_honours_stops_short_of_what_its_field_holds() -> None:
    # The header keeps a word, and FastTracker 2's own editor counts a fadeout up to 0xFFF.
    assert xm_limits(Compliance.CANONICAL).bound(Capability.FADEOUT).maximum == CANONICAL_MAX_FADEOUT
    assert xm_limits(Compliance.EXTENDED).bound(Capability.FADEOUT).maximum == WORD_MAX


def test_a_fadeout_past_the_tracker_is_a_compliance_violation_the_extended_level_allows(
    xm_song: Song,
    xm_voices: InstrumentVoices,
) -> None:
    faster = xm_voices.instruments[0].model_copy(update={"fadeout": 2 * CANONICAL_MAX_FADEOUT})
    quick = revoiced(xm_song, instruments=(faster, *xm_voices.instruments[1:]))
    canonical = XMModule.from_song(quick, compliance=Compliance.CANONICAL).violations()
    assert [violation.capability for violation in canonical] == [Capability.FADEOUT]
    assert canonical[0].severity is Severity.COMPLIANCE
    assert XMModule.from_song(quick, compliance=Compliance.EXTENDED).violations() == ()


def test_this_format_declares_no_song_wide_volume_at_all() -> None:
    limits = xm_limits(Compliance.EXTENDED)
    for capability in (Capability.SONG_VOLUME, Capability.MIX_VOLUME):
        with pytest.raises(KeyError):
            limits.bound(capability)


def test_a_hacked_tempo_is_a_compliance_violation_the_extended_level_allows(xm_song: Song) -> None:
    fast = xm_song.model_copy(update={"playback": Playback(speed=1, tempo=441)})
    canonical = XMModule.from_song(fast, compliance=Compliance.CANONICAL).violations()
    assert [violation.capability for violation in canonical] == [Capability.TEMPO]
    assert canonical[0].severity is Severity.COMPLIANCE
    assert XMModule.from_song(fast, compliance=Compliance.EXTENDED).violations() == ()


def test_extra_channels_are_a_compliance_violation_the_extended_level_allows(xm_song: Song) -> None:
    wide = rescaled(xm_song, 64)
    canonical = XMModule.from_song(wide, compliance=Compliance.CANONICAL).violations()
    assert [violation.capability for violation in canonical] == [Capability.CHANNELS]
    assert XMModule.from_song(wide, compliance=Compliance.EXTENDED).violations() == ()


def test_writing_a_module_the_format_refuses_raises(xm_song: Song) -> None:
    over = rescaled(xm_song, EXTENDED_MAX_CHANNELS + 1)
    with pytest.raises(LimitError) as error:
        XMModule.from_song(over, compliance=Compliance.EXTENDED).to_bytes()

    assert error.value.violations[0].severity is Severity.STRUCTURAL


def test_a_key_above_the_eight_octaves_this_format_numbers_is_reported(
    xm_song: Song,
    xm_voices: InstrumentVoices,
) -> None:
    builder = PatternBuilder(rows=8, channels=1)
    builder.place(0, 0, Cell(note=Note(MAX_NOTE), instrument=0))
    builder.place(1, 0, Cell(note=Note(MAX_NOTE + 1), instrument=0))
    tall = Song(
        name=xm_song.name,
        channels=1,
        patterns=(builder.build(),),
        order=OrderList(entries=(0,)),
        voices=InstrumentVoices(instruments=xm_voices.instruments[:1], samples=xm_voices.samples),
        playback=xm_song.playback,
    )
    reported = [
        violation.capability for violation in XMModule.from_song(tall, compliance=Compliance.EXTENDED).violations()
    ]
    assert reported == [Capability.NOTE]


def test_a_sample_asking_for_gain_this_format_cannot_apply_is_reported(
    xm_song: Song,
    xm_voices: InstrumentVoices,
) -> None:
    # There is no per-sample multiplier here, so anything below full gain has to be baked into the
    # waveform instead — which the report is what tells a caller.
    quiet = xm_voices.samples[0].model_copy(update={"gain": MAX_VOLUME // 2})
    song = revoiced(xm_song, samples=(quiet, *xm_voices.samples[1:]))
    reported = [
        violation.capability for violation in XMModule.from_song(song, compliance=Compliance.EXTENDED).violations()
    ]
    assert reported == [Capability.SAMPLE_GAIN]


PATTERN_ROWS = 32
SPARE_EFFECT = VolumeEffect.VIBRATO_DEPTH
UNNAMED_EFFECT = VolumeEffect.PITCH_SLIDE_UP


def volumed(song: Song, volume: VolumeCommand) -> Song:
    """The song with one pattern stating ``volume``, which is what a volume-column bound is graded over."""
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=song.channels)
    builder.place(0, 0, Cell(note=Note(60), instrument=0, volume=volume))
    return song.model_copy(update={"patterns": (builder.build(),), "order": OrderList.sequential(1)})


def test_the_amounts_a_volume_column_holds_are_bounded_apart_from_its_panning() -> None:
    limits = xm_limits(Compliance.CANONICAL)
    assert limits.bound(Capability.VOLUME_COMMAND).maximum == MAX_VOLUME_COMMAND
    assert limits.bound(Capability.VOLUME_PANNING).maximum == MAX_VOLUME_PANNING


def test_an_amount_past_what_the_column_holds_is_reported(xm_song: Song) -> None:
    past = volumed(xm_song, VolumeCommand(effect=VolumeEffect.VOLUME_SLIDE_UP, amount=MAX_VOLUME_COMMAND + 1))
    (violation,) = XMModule.from_song(past, compliance=Compliance.EXTENDED).violations()
    assert violation.capability is Capability.VOLUME_COMMAND
    assert violation.value == MAX_VOLUME_COMMAND + 1
    assert violation.severity is Severity.STRUCTURAL
    assert violation.subject == "pattern 0"


def test_a_panning_position_is_graded_on_its_own_field(xm_song: Song) -> None:
    # Panning counts a different number of steps from the rates, so the two are bounded apart.
    held = volumed(xm_song, VolumeCommand(effect=VolumeEffect.PANNING, amount=MAX_VOLUME_PANNING))
    assert XMModule.from_song(held, compliance=Compliance.EXTENDED).violations() == ()

    past = volumed(xm_song, VolumeCommand(effect=VolumeEffect.PANNING, amount=MAX_VOLUME_PANNING + 1))
    (violation,) = XMModule.from_song(past, compliance=Compliance.EXTENDED).violations()
    assert violation.capability is Capability.VOLUME_PANNING


def test_a_pattern_states_one_violation_per_quantity_however_many_cells_carry_one(xm_song: Song) -> None:
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=xm_song.channels)
    for row, amount in enumerate((MAX_VOLUME_COMMAND + 1, MAX_VOLUME_COMMAND + 3, MAX_VOLUME_COMMAND + 2)):
        builder.place(row, 0, Cell(note=Note(60), volume=VolumeCommand(effect=SPARE_EFFECT, amount=amount)))

    crowded = xm_song.model_copy(update={"patterns": (builder.build(),), "order": OrderList.sequential(1)})
    (violation,) = XMModule.from_song(crowded, compliance=Compliance.EXTENDED).violations()
    assert violation.value == MAX_VOLUME_COMMAND + 3


def test_an_effect_this_column_has_no_run_for_raises_where_it_is_met(xm_song: Song) -> None:
    # A bound says use a smaller number; content the column cannot state at all has no bound to report.
    unnamed = volumed(xm_song, VolumeCommand(effect=UNNAMED_EFFECT, amount=0))
    module = XMModule.from_song(unnamed, compliance=Compliance.EXTENDED)
    assert module.violations() == ()
    with pytest.raises(ValueError, match="no run for"):
        module.to_bytes()

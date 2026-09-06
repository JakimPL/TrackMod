import pytest

from tests.conftest import rescaled, revoiced
from tests.trackers.xm.conftest import xm_pattern
from trackmod.core.envelopes.kind import EnvelopeKind
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.repairs.report import Repairs
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
from trackmod.trackers.xm.instruments.envelope import parse_envelope
from trackmod.trackers.xm.layout.envelope import envelope_field
from trackmod.trackers.xm.limits import xm_limits
from trackmod.trackers.xm.module import XMModule
from trackmod.trackers.xm.spec.flags import EnvelopeFlag
from trackmod.trackers.xm.spec.ranges import (
    CANONICAL_MAX_CHANNELS,
    CANONICAL_MAX_FADEOUT,
    CANONICAL_MAX_ORDERS,
    CANONICAL_MAX_PATTERNS,
    CANONICAL_MAX_TEMPO,
    ENVELOPE_LEVELS,
    EXTENDED_MAX_CHANNELS,
    EXTENDED_MAX_ROWS,
    EXTENDED_MAX_TEMPO,
    MAX_NOTE,
    MAX_VOLUME_COMMAND,
    MAX_VOLUME_PANNING,
)


def test_the_tempo_word_is_where_this_format_has_its_headroom() -> None:
    # The header stores the tempo in sixteen bits while the tracker honours one byte of it, which is
    # the whole reason a caller reaching for a shorter row chooses this format. The players descended
    # from it stop partway up that word, so all three ceilings differ here.
    assert xm_limits(Compliance.CANONICAL).bound(Capability.TEMPO).maximum == CANONICAL_MAX_TEMPO
    assert xm_limits(Compliance.EXTENDED).bound(Capability.TEMPO).maximum == EXTENDED_MAX_TEMPO
    assert xm_limits(Compliance.STRUCTURAL).bound(Capability.TEMPO).maximum == WORD_MAX


def test_the_channel_count_has_headroom_too() -> None:
    assert xm_limits(Compliance.CANONICAL).bound(Capability.CHANNELS).maximum == CANONICAL_MAX_CHANNELS
    assert xm_limits(Compliance.EXTENDED).bound(Capability.CHANNELS).maximum == EXTENDED_MAX_CHANNELS


def test_the_counts_the_tracker_edited_stop_short_of_the_header_words() -> None:
    # The header states both counts in sixteen bits, and the editor stopped at 256 of each.
    for capability, edited in (
        (Capability.PATTERNS, CANONICAL_MAX_PATTERNS),
        (Capability.ORDERS, CANONICAL_MAX_ORDERS),
    ):
        assert xm_limits(Compliance.EXTENDED).bound(capability).maximum == edited
        assert xm_limits(Compliance.STRUCTURAL).bound(capability).maximum == WORD_MAX


def test_the_sample_slots_a_module_holds_are_what_its_two_counts_multiply_to() -> None:
    # Samples live inside instruments here, so how many a module holds is a product rather than a field
    # of its own, and it widens exactly as far as its two factors do.
    for compliance in (Compliance.CANONICAL, Compliance.STRUCTURAL):
        limits = xm_limits(compliance)
        instruments = limits.bound(Capability.INSTRUMENTS).maximum
        per_instrument = limits.bound(Capability.SAMPLES_PER_INSTRUMENT).maximum
        assert limits.bound(Capability.SAMPLES).maximum == instruments * per_instrument


def test_more_patterns_than_the_tracker_edited_are_reported_and_the_word_still_holds_them(xm_song: Song) -> None:
    many = xm_song.model_copy(
        update={
            "patterns": tuple(xm_song.patterns[0] for _ in range(CANONICAL_MAX_PATTERNS + 1)),
            "order": OrderList(entries=(0,)),
        }
    )
    assert XMModule.from_song(many, compliance=Compliance.STRUCTURAL).violations() == ()

    (reported,) = XMModule.from_song(many, compliance=Compliance.EXTENDED).violations()
    assert reported.capability is Capability.PATTERNS
    assert reported.severity is Severity.EXTENDED


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
        with pytest.raises(ValueError, match=f"keeps no field for {capability.value}"):
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


def test_writing_a_module_wider_than_any_player_reads_raises(xm_song: Song) -> None:
    over = rescaled(xm_song, EXTENDED_MAX_CHANNELS + 1)
    with pytest.raises(LimitError) as error:
        XMModule.from_song(over, compliance=Compliance.EXTENDED).to_bytes()

    assert error.value.violations[0].severity is Severity.EXTENDED


def test_a_width_the_header_word_still_holds_is_written_at_the_widest_level(xm_song: Song) -> None:
    # The header counts channels in sixteen bits, so a width past what any player reads is still a
    # width the bytes hold — which is what the widest level is for.
    over = rescaled(xm_song, EXTENDED_MAX_CHANNELS + 1)
    module = XMModule.from_song(over, compliance=Compliance.STRUCTURAL)
    assert module.violations() == ()
    assert module.reach is Compliance.STRUCTURAL


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


def test_a_pattern_taller_than_the_tracker_edits_is_read_and_written_back(xm_song: Song) -> None:
    # The pattern header states its height in sixteen bits while FastTracker 2 edits 256 rows, and the
    # players descended from it read four times that. A file holding one has to survive a round trip.
    tall = xm_pattern(rows=EXTENDED_MAX_ROWS, channels=4, instruments=2, seed=5)
    stretched = xm_song.model_copy(update={"patterns": (tall,), "order": OrderList(entries=(0,))})
    module = XMModule.from_song(stretched, compliance=Compliance.EXTENDED)

    assert module.violations() == ()
    assert module.reach is Compliance.EXTENDED
    assert XMModule.parse(module.to_bytes()).song.patterns[0].rows == EXTENDED_MAX_ROWS


def test_a_tempo_past_what_the_players_read_is_reported_before_the_word_runs_out(xm_song: Song) -> None:
    beyond = xm_song.model_copy(update={"playback": Playback(speed=6, tempo=EXTENDED_MAX_TEMPO + 1)})
    (reported,) = XMModule.from_song(beyond, compliance=Compliance.EXTENDED).violations()
    assert reported.capability is Capability.TEMPO
    assert reported.severity is Severity.EXTENDED
    assert XMModule.from_song(beyond, compliance=Compliance.STRUCTURAL).violations() == ()


def test_a_stored_envelope_level_past_the_field_is_drawn_inside_it() -> None:
    # Trackers leave the node table past the count they use as they found it, so files state levels in
    # nodes no curve reaches. Reading one as it stands would make a file this library just read
    # unwritable, which is what the repair path is for.
    values = {
        envelope_field(EnvelopeKind.VOLUME, "flags"): int(EnvelopeFlag.ENABLED),
        envelope_field(EnvelopeKind.VOLUME, "count"): 2,
        envelope_field(EnvelopeKind.VOLUME, "sustain"): 0,
        envelope_field(EnvelopeKind.VOLUME, "loop_begin"): 0,
        envelope_field(EnvelopeKind.VOLUME, "loop_end"): 0,
        envelope_field(EnvelopeKind.VOLUME, "points"): ((0, 64), (32, 4112)),
    }
    repairs = Repairs()
    envelope = parse_envelope(EnvelopeKind.VOLUME, values, subject="instrument 0", repairs=repairs)

    assert envelope is not None
    assert [point.value for point in envelope.points] == [MAX_VOLUME, MAX_VOLUME]
    assert repairs.entries == (("instrument 0", f"1 envelope levels drawn inside {ENVELOPE_LEVELS}"),)

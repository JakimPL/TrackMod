import numpy as np
import pytest

from tests.conftest import lattice, rescaled
from tests.trackers.s3m.conftest import S3M_CHANNELS, s3m_pattern
from trackmod.core.effects.effect import Effect
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.grid import Pattern
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import SampleVoices
from trackmod.core.volumes.command import VolumeCommand, VolumeEffect
from trackmod.limits.capability import Capability
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import LimitError
from trackmod.spec.pitch import REFERENCE_RATE
from trackmod.spec.width import BYTE_MAX
from trackmod.trackers.s3m.limits import s3m_limits
from trackmod.trackers.s3m.module import S3MModule
from trackmod.trackers.s3m.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.s3m.spec.keys import CANONICAL_MAX_NOTE, CANONICAL_MIN_NOTE, MAX_NOTE
from trackmod.trackers.s3m.spec.ranges import (
    CANONICAL_MAX_CHANNELS,
    CANONICAL_MAX_SAMPLE_BYTES,
    CANONICAL_MAX_SAMPLE_FRAMES,
    CANONICAL_MAX_SAMPLE_RATE,
    MAX_BLOCK_OFFSET,
    MAX_GLOBAL_VOLUME,
    PATTERN_ROWS,
    STRUCTURAL_MAX_CHANNELS,
)


def bound(compliance: Compliance, capability: Capability) -> tuple[int, int]:
    reached = s3m_limits(compliance).bound(capability)
    return reached.minimum, reached.maximum


@pytest.mark.parametrize(
    ("capability", "canonical", "wider"),
    [
        (Capability.CHANNELS, CANONICAL_MAX_CHANNELS, STRUCTURAL_MAX_CHANNELS),
        (Capability.NOTE, CANONICAL_MAX_NOTE, MAX_NOTE),
        (Capability.SAMPLE_FRAMES, CANONICAL_MAX_SAMPLE_FRAMES, 0xFFFFFFFF),
        (Capability.SAMPLE_RATE, CANONICAL_MAX_SAMPLE_RATE, 0xFFFFFFFF),
        (Capability.PATTERNS, 100, 254),
        (Capability.SAMPLES, 99, 255),
    ],
)
def test_the_editor_stops_short_of_what_the_records_hold(capability: Capability, canonical: int, wider: int) -> None:
    assert bound(Compliance.CANONICAL, capability)[1] == canonical
    assert bound(Compliance.EXTENDED, capability)[1] == wider
    assert bound(Compliance.STRUCTURAL, capability)[1] == wider


PACKED_PATTERNS = 90


def crowded_pattern() -> Pattern:
    """A pattern stating every column of every cell, which is the largest block this format packs."""
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=STRUCTURAL_MAX_CHANNELS)
    for row in range(PATTERN_ROWS):
        for channel in range(STRUCTURAL_MAX_CHANNELS):
            builder.place(
                row,
                channel,
                Cell(note=Note(60), instrument=0, volume=32, effect=Effect(command=1, parameter=1)),
            )

    return builder.build()


def test_a_song_reaching_past_what_a_pointer_names_is_reported_rather_than_overflowing() -> None:
    # Every block is found by the paragraph its pointer names, so a module of enough full patterns runs
    # past what two bytes reach -- a quantity, and one the writer would otherwise meet as an overflow.
    crowded = crowded_pattern()
    song = keyed_song(60).model_copy(
        update={
            "channels": STRUCTURAL_MAX_CHANNELS,
            "patterns": tuple(crowded for _ in range(PACKED_PATTERNS)),
        }
    )
    module = S3MModule.from_song(song, compliance=Compliance.STRUCTURAL)

    (reported,) = module.violations()
    assert reported.capability is Capability.BLOCK_OFFSET
    assert reported.level is Compliance.STRUCTURAL
    assert reported.bound.maximum == MAX_BLOCK_OFFSET

    with pytest.raises(LimitError, match="block_offset"):
        module.to_bytes()


def test_the_song_volume_stops_where_the_tracker_did_and_its_byte_holds_more() -> None:
    assert bound(Compliance.EXTENDED, Capability.SONG_VOLUME)[1] == MAX_GLOBAL_VOLUME
    assert bound(Compliance.STRUCTURAL, Capability.SONG_VOLUME)[1] == BYTE_MAX


def test_every_pattern_of_this_format_is_the_same_height() -> None:
    for compliance in Compliance:
        assert bound(compliance, Capability.PATTERN_ROWS) == (PATTERN_ROWS, PATTERN_ROWS)


def test_a_song_inside_the_tracker_reaches_no_further(s3m_song: Song) -> None:
    module = S3MModule.from_song(s3m_song, compliance=Compliance.CANONICAL)
    assert module.violations() == ()
    assert module.exceeded() == ()
    assert module.reach is Compliance.CANONICAL


def test_a_song_wider_than_the_tracker_mixed_reaches_the_level_above_it(s3m_song: Song) -> None:
    wide = S3MModule.from_song(rescaled(s3m_song, 24), compliance=Compliance.EXTENDED)
    assert wide.violations() == ()
    assert wide.reach is Compliance.EXTENDED
    assert [violation.capability for violation in wide.exceeded()] == [Capability.CHANNELS]
    assert wide.exceeded()[0].level is Compliance.CANONICAL
    with pytest.raises(LimitError, match="channels"):
        wide.require_reach(Compliance.CANONICAL)


def test_a_song_wider_than_the_settings_table_is_refused_at_every_level(s3m_song: Song) -> None:
    beyond = S3MModule.from_song(rescaled(s3m_song, STRUCTURAL_MAX_CHANNELS + 1), compliance=Compliance.STRUCTURAL)
    violations = beyond.violations()
    assert [violation.capability for violation in violations] == [Capability.CHANNELS]
    assert violations[0].level is Compliance.STRUCTURAL


def keyed_song(key: int) -> Song:
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=1)
    builder.place(0, 0, Cell(note=Note(key), instrument=0))
    return Song(
        name="keyed",
        channels=1,
        patterns=(builder.build(),),
        order=OrderList(entries=(0,)),
        voices=SampleVoices(samples=(Sample(name="lead", pcm=lattice(np.zeros(8)), rate=REFERENCE_RATE),)),
        playback=Playback(speed=DEFAULT_SPEED, tempo=DEFAULT_TEMPO),
    )


def test_the_deepest_key_a_pattern_plays_is_graded_beside_the_highest() -> None:
    # This format numbers its lowest octave an octave above the model's, so its keyboard has a floor as
    # well as a ceiling and a pattern reaching below it is reported even where its highest key sits
    # comfortably inside.
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=1)
    builder.place(0, 0, Cell(note=Note(CANONICAL_MIN_NOTE - 1), instrument=0))
    builder.place(1, 0, Cell(note=Note(CANONICAL_MAX_NOTE), instrument=0))
    deep = keyed_song(60).model_copy(update={"patterns": (builder.build(),)})

    (reported,) = S3MModule.from_song(deep, compliance=Compliance.CANONICAL).violations()
    assert reported.capability is Capability.NOTE
    assert reported.value == CANONICAL_MIN_NOTE - 1


def test_a_key_above_the_octaves_the_editor_spells_reaches_past_the_tracker() -> None:
    module = S3MModule.from_song(keyed_song(CANONICAL_MAX_NOTE + 1), compliance=Compliance.EXTENDED)
    assert module.violations() == ()
    assert module.reach is Compliance.EXTENDED
    assert [violation.capability for violation in module.exceeded()] == [Capability.NOTE]


def sampled_song(sample: Sample) -> Song:
    """A song carrying one waveform, which is how a sample bound is exercised on its own."""
    return keyed_song(60).model_copy(update={"voices": SampleVoices(samples=(sample,))})


def test_a_sample_longer_than_the_tracker_stored_reaches_past_it() -> None:
    long = Sample(
        name="long",
        pcm=lattice(np.zeros(CANONICAL_MAX_SAMPLE_FRAMES + 1), BitDepth.EIGHT),
        rate=REFERENCE_RATE,
        depth=BitDepth.EIGHT,
    )
    module = S3MModule.from_song(sampled_song(long), compliance=Compliance.EXTENDED)
    assert module.violations() == ()
    assert [violation.capability for violation in module.exceeded()] == [
        Capability.SAMPLE_FRAMES,
        Capability.SAMPLE_BYTES,
    ]


def test_a_wide_sample_inside_the_frames_the_tracker_loaded_states_the_block_it_comes_to() -> None:
    frames = CANONICAL_MAX_SAMPLE_BYTES // 2
    wide = Sample(
        name="wide",
        pcm=lattice(np.zeros((frames, 2))),
        rate=REFERENCE_RATE,
    )
    module = S3MModule.from_song(sampled_song(wide), compliance=Compliance.EXTENDED)
    assert module.violations() == ()
    (reported,) = module.exceeded()
    assert reported.capability is Capability.SAMPLE_BYTES
    assert reported.value == frames * 2 * 2


def test_a_rate_past_the_word_the_tracker_read_reaches_past_it() -> None:
    fast = Sample(name="fast", pcm=lattice(np.zeros(8)), rate=CANONICAL_MAX_SAMPLE_RATE + 1)
    song = keyed_song(60).model_copy(update={"voices": SampleVoices(samples=(fast,))})
    module = S3MModule.from_song(song, compliance=Compliance.EXTENDED)
    assert module.violations() == ()
    assert [violation.capability for violation in module.exceeded()] == [Capability.SAMPLE_RATE]


def test_what_a_file_reaches_survives_being_written_and_read_back(s3m_song: Song) -> None:
    wide = S3MModule.from_song(rescaled(s3m_song, 24), compliance=Compliance.EXTENDED)
    assert S3MModule.parse(wide.to_bytes()).reach is Compliance.EXTENDED


def test_a_song_the_tracker_mixed_is_narrower_than_the_table_that_states_it(s3m_song: Song) -> None:
    module = S3MModule.from_song(rescaled(s3m_song, CANONICAL_MAX_CHANNELS), compliance=Compliance.CANONICAL)
    assert module.violations() == ()
    assert module.reach is Compliance.CANONICAL
    assert len(s3m_pattern(channels=S3M_CHANNELS, samples=1, seed=1).note[0]) == S3M_CHANNELS


def test_a_column_intent_this_format_states_no_run_for_is_refused_where_it_is_written(
    s3m_song: Song,
) -> None:
    # An intent the column has no run for is content this format has no encoding for, so it is graded
    # nowhere and refused by name at the point the bytes are made -- as it is in every other format.
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=S3M_CHANNELS)
    builder.place(0, 0, Cell(volume=VolumeCommand(effect=VolumeEffect.VOLUME_SLIDE_UP, amount=3)))
    song = s3m_song.model_copy(update={"patterns": (builder.build(),), "order": OrderList(entries=(0,))})
    module = S3MModule.from_song(song, compliance=Compliance.CANONICAL)
    assert module.violations() == ()
    assert module.reach is Compliance.CANONICAL
    with pytest.raises(ValueError, match="no run for VOLUME_SLIDE_UP"):
        module.to_bytes()


def test_a_panning_amount_past_the_run_that_holds_it_is_graded(s3m_song: Song) -> None:
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=S3M_CHANNELS)
    builder.place(0, 0, Cell(volume=VolumeCommand(effect=VolumeEffect.PANNING, amount=100)))
    song = s3m_song.model_copy(update={"patterns": (builder.build(),), "order": OrderList(entries=(0,))})
    violations = S3MModule.from_song(song, compliance=Compliance.CANONICAL).violations()
    assert [violation.capability for violation in violations] == [Capability.VOLUME_PANNING]

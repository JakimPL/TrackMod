import numpy as np
import pytest

from tests.conftest import lattice, rescaled
from tests.trackers.s3m.conftest import S3M_CHANNELS, s3m_pattern
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import SampleVoices
from trackmod.limits.capability import Capability
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import LimitError
from trackmod.limits.severity import Severity
from trackmod.spec.pitch import REFERENCE_RATE
from trackmod.trackers.s3m.limits import s3m_limits
from trackmod.trackers.s3m.module import S3MModule
from trackmod.trackers.s3m.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.s3m.spec.keys import CANONICAL_MAX_NOTE, MAX_NOTE
from trackmod.trackers.s3m.spec.ranges import (
    CANONICAL_MAX_CHANNELS,
    CANONICAL_MAX_SAMPLE_FRAMES,
    CANONICAL_MAX_SAMPLE_RATE,
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
    assert wide.exceeded()[0].severity is Severity.COMPLIANCE
    with pytest.raises(LimitError, match="channels"):
        wide.require_reach(Compliance.CANONICAL)


def test_a_song_wider_than_the_settings_table_is_refused_at_every_level(s3m_song: Song) -> None:
    beyond = S3MModule.from_song(rescaled(s3m_song, STRUCTURAL_MAX_CHANNELS + 1), compliance=Compliance.STRUCTURAL)
    violations = beyond.violations()
    assert [violation.capability for violation in violations] == [Capability.CHANNELS]
    assert violations[0].severity is Severity.STRUCTURAL


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


def test_a_key_above_the_octaves_the_editor_spells_reaches_past_the_tracker() -> None:
    module = S3MModule.from_song(keyed_song(CANONICAL_MAX_NOTE + 1), compliance=Compliance.EXTENDED)
    assert module.violations() == ()
    assert module.reach is Compliance.EXTENDED
    assert [violation.capability for violation in module.exceeded()] == [Capability.NOTE]


def test_a_sample_longer_than_the_tracker_stored_reaches_past_it() -> None:
    long = Sample(
        name="long",
        pcm=lattice(np.zeros(CANONICAL_MAX_SAMPLE_FRAMES + 1)),
        rate=REFERENCE_RATE,
    )
    song = keyed_song(60).model_copy(update={"voices": SampleVoices(samples=(long,))})
    module = S3MModule.from_song(song, compliance=Compliance.EXTENDED)
    assert module.violations() == ()
    assert [violation.capability for violation in module.exceeded()] == [Capability.SAMPLE_FRAMES]


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

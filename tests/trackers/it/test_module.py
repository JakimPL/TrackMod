from pathlib import Path

import numpy as np
import pytest

from tests.conftest import make_sample
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.songs.song import Song
from trackmod.limits.compliance import Compliance
from trackmod.spec.pitch import NOTE_COUNT
from trackmod.trackers.it.module import ITModule
from trackmod.trackers.it.patterns.sizing import packed_bytes
from trackmod.trackers.it.settings import ITSettings
from trackmod.trackers.it.spec.identity import (
    MAGIC_INSTRUMENT,
    MAGIC_MODULE,
    MAGIC_SAMPLE,
)
from trackmod.trackers.it.spec.storage import IT_STORAGE
from trackmod.trackers.it.version import Tracker, wrote

EXTRA_FRAMES = 64
EXTRA_CHANNELS = 5


def module(song: Song, *, compliance: Compliance = Compliance.EXTENDED) -> ITModule:
    return ITModule.from_song(song, compliance=compliance)


def test_every_section_opens_with_its_own_tag(song: Song) -> None:
    data = module(song).to_bytes()
    assert data.startswith(MAGIC_MODULE)
    assert MAGIC_INSTRUMENT in data
    assert MAGIC_SAMPLE in data


def test_the_size_model_agrees_with_the_written_file(song: Song) -> None:
    assert module(song).size().total == len(module(song).to_bytes())


def test_the_size_report_names_the_largest_pattern(song: Song) -> None:
    report = module(song).size()
    assert report.largest_pattern == max(packed_bytes(pattern) for pattern in song.patterns)
    assert report.total == report.patterns + report.pcm + report.headers


def test_one_more_sample_grows_the_file_by_what_the_table_charges(song: Song) -> None:
    extra = make_sample("extra", frames=EXTRA_FRAMES, seed=99)
    grown = song.model_copy(update={"samples": (*song.samples, extra)})
    growth = len(module(grown).to_bytes()) - len(module(song).to_bytes())
    assert growth == IT_STORAGE.sample_bytes(frames=extra.frames, depth=extra.depth)


def test_one_more_instrument_grows_the_file_by_what_the_table_charges(song: Song) -> None:
    placeholder = Instrument(name="silent", keymap=(None,) * NOTE_COUNT)
    grown = song.model_copy(update={"instruments": (*song.instruments, placeholder)})
    growth = len(module(grown).to_bytes()) - len(module(song).to_bytes())
    assert growth == IT_STORAGE.instrument_bytes(samples=0)


def test_a_written_module_parses_back_to_the_same_song(song: Song) -> None:
    recovered = ITModule.parse(module(song).to_bytes()).song
    assert recovered.name == song.name
    assert recovered.channels == song.channels
    assert recovered.playback == song.playback
    assert recovered.order.entries == song.order.entries
    assert recovered.instruments == song.instruments
    assert recovered.patterns == song.patterns


def test_a_song_wider_than_the_notes_it_plays_parses_back_at_its_own_width(song: Song) -> None:
    # The format states a channel count nowhere, so the width comes back out of the patterns: a song
    # holding channels in reserve — a stereo pair rounded up to, a part yet to be written — keeps them
    # because each pattern names its widest channel.
    widened = song.model_copy(
        update={
            "channels": song.channels + EXTRA_CHANNELS,
            "patterns": tuple(pattern.widened(song.channels + EXTRA_CHANNELS) for pattern in song.patterns),
        }
    )
    recovered = ITModule.parse(module(widened).to_bytes()).song
    assert recovered.channels == widened.channels
    assert recovered.patterns == widened.patterns


def test_sample_headers_and_waveforms_survive_a_round_trip(song: Song) -> None:
    recovered = ITModule.parse(module(song).to_bytes()).song
    for original, restored in zip(song.samples, recovered.samples):
        assert restored.name == original.name
        assert restored.rate == original.rate
        assert restored.depth == original.depth
        assert restored.loop == original.loop
        assert np.allclose(restored.pcm, original.pcm, atol=1.5 / original.depth.scale)


def test_settings_survive_a_round_trip(song: Song) -> None:
    settings = ITSettings(global_volume=96, mix_volume=64)
    written = ITModule(song=song, compliance=Compliance.EXTENDED, settings=settings).to_bytes()
    assert ITModule.parse(written).settings == settings


def test_a_written_module_can_be_saved_and_loaded(tmp_path: Path, song: Song) -> None:
    path = tmp_path / f"song{module(song).extension}"
    module(song).save(path)
    assert ITModule.load(path).song.name == song.name


def test_parsing_something_that_is_not_a_module_raises() -> None:
    with pytest.raises(ValueError):
        ITModule.parse(b"not a module" + bytes(256))


def test_a_module_keeps_the_version_of_whatever_wrote_it(song: Song) -> None:
    # Reading a file and writing it back leaves it stating the program it arrived from, not this one.
    written = ITModule.from_song(song, compliance=Compliance.EXTENDED, settings=ITSettings(created_with=0x5132))
    recovered = ITModule.parse(written.to_bytes())
    assert recovered.settings.created_with == 0x5132
    assert wrote(recovered.settings.created_with) is Tracker.OPEN_MPT


def test_a_song_built_from_nothing_states_the_version_this_format_writes(song: Song) -> None:
    recovered = ITModule.parse(ITModule.from_song(song, compliance=Compliance.EXTENDED).to_bytes())
    assert wrote(recovered.settings.created_with) is Tracker.IMPULSE_TRACKER

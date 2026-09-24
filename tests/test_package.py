import importlib.metadata
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest

import trackmod
from trackmod import (
    MODULE_EXTENSIONS,
    BitDepth,
    Compliance,
    InstrumentUnit,
    InstrumentVoices,
    ITInstrumentFile,
    ITModule,
    Loop,
    MODModule,
    S3MModule,
    Sample,
    Song,
    STModule,
    XMInstrumentFile,
    XMModule,
    flattened,
    load_module,
    load_sample,
    load_voices,
    save_sample,
    units,
    write_sample,
)
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.keymap import pitched_keymap
from trackmod.core.patterns.grid import Pattern
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.spec.pitch import REFERENCE_RATE

RATE = 44100
FRAMES = 32
VOICES = 3
CHANNELS = 4

VOICED_BINDINGS = (ITModule, XMModule)
SAMPLED_BINDINGS = (MODModule, S3MModule, STModule)
BINDINGS = VOICED_BINDINGS + SAMPLED_BINDINGS
INSTRUMENT_BINDINGS = (ITInstrumentFile, XMInstrumentFile)


def make_sample(index: int) -> Sample:
    """One waveform every format here holds: eight bits, one channel, at the rate the Amiga clocked."""
    rng = np.random.default_rng(index)
    return Sample(
        name=f"voice {index}",
        pcm=rng.uniform(-1.0, 1.0, FRAMES),
        rate=REFERENCE_RATE,
        depth=BitDepth.EIGHT,
        loop=Loop(begin=8, end=FRAMES),
    )


@pytest.fixture
def collection(tmp_path: Path) -> Path:
    """One song written once by every format, under names stating none of them.

    A collection reaches a reader the way it sat on disk, and what a file is called there says less
    than what it holds, so each name here carries a suffix no format writes. Three of the five address
    their voices as plain samples, and the song reaches those flattened onto the table they hold.
    """
    voices = InstrumentVoices(
        instruments=tuple(
            Instrument(name=f"voice {index}", keymap=pitched_keymap(sample=index)) for index in range(VOICES)
        ),
        samples=tuple(make_sample(index) for index in range(VOICES)),
    )
    song = Song(
        name="collected",
        channels=CHANNELS,
        patterns=(Pattern.empty(rows=64, channels=CHANNELS),),
        order=OrderList(entries=(0,)),
        voices=voices,
        playback=Playback(speed=6, tempo=125),
    )
    holder = tmp_path / "collection"
    holder.mkdir()
    sampled = song.model_copy(update={"voices": flattened(voices)})
    for index, binding in enumerate(BINDINGS):
        held = song if binding in VOICED_BINDINGS else sampled
        binding.from_song(held, compliance=Compliance.CANONICAL).save(holder / f"{index}.dat")

    return holder


def test_the_package_root_offers_every_name_it_states() -> None:
    assert [name for name in trackmod.__all__ if not hasattr(trackmod, name)] == []


def test_the_package_root_states_every_name_it_offers() -> None:
    # Anything reachable from the root is part of the surface, so the two lists are one list.
    reachable = {
        name for name, value in vars(trackmod).items() if not name.startswith("_") and not isinstance(value, ModuleType)
    }
    assert reachable == set(trackmod.__all__)


def test_the_package_states_the_version_it_was_installed_as() -> None:
    assert trackmod.__version__ == importlib.metadata.version("trackmod")


def test_a_collection_opens_as_whatever_wrote_each_file(collection: Path) -> None:
    for path in sorted(collection.iterdir()):
        module = load_module(path)
        assert module.extension in MODULE_EXTENSIONS
        assert len(module.song.voices.samples) == VOICES


def test_every_instrument_of_a_collection_reaches_a_file_of_its_own(collection: Path, tmp_path: Path) -> None:
    # The loop the guide shows: open each file, reach the voices inside it, write each one out.
    holder = tmp_path / "instruments"
    holder.mkdir()
    for path in sorted(collection.iterdir()):
        for index, unit in enumerate(units(load_module(path).song.voices)):
            assert isinstance(unit, InstrumentUnit)
            for binding in INSTRUMENT_BINDINGS:
                file = binding.from_unit(unit, compliance=Compliance.CANONICAL)
                file.save(holder / f"{path.stem}-{index:02d}{file.extension}")

    assert len(list(holder.iterdir())) == len(BINDINGS) * len(INSTRUMENT_BINDINGS) * VOICES


def test_every_waveform_of_a_collection_reaches_an_audio_file(collection: Path, tmp_path: Path) -> None:
    holder = tmp_path / "waveforms"
    holder.mkdir()
    for path in sorted(collection.iterdir()):
        for index, sample in enumerate(load_voices(path).samples):
            target = holder / f"{path.stem}-{index:02d}.wav"
            save_sample(sample, target)
            read = load_sample(target)
            assert (read.frames, read.rate, read.loop) == (sample.frames, sample.rate, sample.loop)

    assert len(list(holder.iterdir())) == len(BINDINGS) * VOICES


def test_a_waveform_written_from_the_root_reads_back_from_the_root() -> None:
    sample = Sample(name="lead", pcm=np.zeros(16), rate=RATE, depth=BitDepth.EIGHT, loop=Loop(begin=0, end=16))
    assert trackmod.parse_sample(write_sample(sample)) == sample

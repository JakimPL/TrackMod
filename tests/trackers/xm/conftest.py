import numpy as np
import pytest

from tests.conftest import keyed, lattice
from trackmod.core.effects.effect import Effect
from trackmod.core.envelopes.envelope import Envelope
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.notes.command import NoteCommand
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.grid import Pattern
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.song import Song
from trackmod.spec.levels import MAX_VOLUME
from trackmod.spec.pitch import RATE_NOTE
from trackmod.spec.width import BYTE_MAX
from trackmod.trackers.xm.spec.ranges import MAX_NOTE, PAN_CENTER
from trackmod.trackers.xm.tuning import Tuning, tuning_for


def xm_pattern(*, rows: int, channels: int, instruments: int, seed: int) -> Pattern:
    """A grid covering every combination of present and absent columns, inside this format's keys."""
    rng = np.random.default_rng(seed)
    builder = PatternBuilder(rows=rows, channels=channels)
    for row in range(rows):
        for channel in range(channels):
            draw = rng.random()
            if draw < 0.25:
                continue

            note = Note(int(rng.integers(0, MAX_NOTE + 1))) if draw < 0.85 else NoteCommand.OFF
            builder.place(
                row,
                channel,
                Cell(
                    note=note,
                    instrument=int(rng.integers(0, instruments)) if draw < 0.8 else None,
                    volume=int(rng.integers(0, MAX_VOLUME + 1)) if draw < 0.7 else None,
                    effect=Effect(command=1, parameter=int(rng.integers(0, BYTE_MAX + 1))) if draw > 0.9 else None,
                ),
            )

    return builder.build()


def _tuning_of(rate: int) -> Tuning:
    """The tuning this format's writer derives for a sample sounded, untransposed, at its own rate.

    Every instrument below maps each key to its own pitch, so every key a sample sounds at leaves it
    untransposed -- the one case `tuning_for` gives the same answer at, regardless of which key it is.
    """
    reference = Note(RATE_NOTE)
    return tuning_for(rate, key=reference, sounded=reference)


@pytest.fixture
def xm_song(fade_envelope: Envelope) -> Song:
    """A song this format can write and read back unchanged.

    Every instrument owns its own samples in order, every key sounds its own pitch, every sample states
    a panning, and the rates already sit on the tuning lattice — so a round trip changes nothing and any
    difference a test finds is a real one. Each sample's own `relative_note`/`finetune` are stated to
    match the tuning its rate derives, since that is the only pair a real parsed file could ever hold
    for a rate: TrackMod's XM parser always derives both from the same header bytes together.
    """
    lead_tuning = _tuning_of(44092)
    bass_tuning = _tuning_of(22046)
    samples = (
        Sample(
            name="lead",
            pcm=lattice(np.linspace(-1.0, 1.0, 32)),
            rate=44092,
            panning=PAN_CENTER,
            relative_note=lead_tuning.relative_note,
            finetune=lead_tuning.finetune,
        ),
        Sample(
            name="bass",
            pcm=lattice(np.linspace(1.0, -1.0, 24), BitDepth.EIGHT),
            rate=22046,
            depth=BitDepth.EIGHT,
            volume=48,
            panning=64,
            relative_note=bass_tuning.relative_note,
            finetune=bass_tuning.finetune,
        ),
        Sample(
            name="looped",
            pcm=lattice(np.linspace(-1.0, 1.0, 48)),
            rate=44092,
            panning=PAN_CENTER,
            loop=Loop(begin=8, end=40, mode=LoopMode.FORWARD),
            relative_note=lead_tuning.relative_note,
            finetune=lead_tuning.finetune,
        ),
    )
    instruments = (
        Instrument(name="piano", keymap=keyed(sample=0), volume_envelope=fade_envelope, fadeout=256),
        Instrument(name="bass", keymap=keyed(sample=1)),
        Instrument(name="pad", keymap=keyed(sample=2)),
    )
    return Song(
        name="trackmod",
        channels=4,
        patterns=(
            xm_pattern(rows=32, channels=4, instruments=len(instruments), seed=11),
            xm_pattern(rows=16, channels=4, instruments=len(instruments), seed=12),
        ),
        order=OrderList(entries=(0, 1, 0), restart=1),
        instruments=instruments,
        samples=samples,
        playback=Playback(speed=6, tempo=125),
    )

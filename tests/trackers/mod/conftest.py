import struct

import numpy as np
import pytest

from tests.conftest import lattice
from trackmod.core.effects.effect import Effect
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
from trackmod.core.voices.voices import SampleVoices
from trackmod.spec.pitch import REFERENCE_RATE
from trackmod.spec.width import BYTE_MAX
from trackmod.trackers.mod.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.mod.spec.periods import (
    CANONICAL_MAX_NOTE,
    CANONICAL_MIN_NOTE,
    FINETUNE_RATES,
)
from trackmod.trackers.mod.spec.ranges import CANONICAL_CHANNELS, PATTERN_ROWS
from trackmod.trackers.mod.spec.sizes import (
    MODULE_NAME_BYTES,
    NAME_BYTES,
    ORDER_TABLE_BYTES,
    SAMPLE_SLOTS,
)

RECORD_FORMAT = ">HBBHH"


def mod_pattern(*, channels: int, samples: int, seed: int) -> Pattern:
    """A grid inside the keys this format tabulates, covering the columns a cell here carries."""
    rng = np.random.default_rng(seed)
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=channels)
    for row in range(PATTERN_ROWS):
        for channel in range(channels):
            draw = rng.random()
            if draw < 0.25:
                continue

            builder.place(
                row,
                channel,
                Cell(
                    note=Note(int(rng.integers(CANONICAL_MIN_NOTE, CANONICAL_MAX_NOTE + 1))) if draw < 0.85 else None,
                    instrument=int(rng.integers(0, samples)) if draw < 0.8 else None,
                    effect=Effect(command=1, parameter=int(rng.integers(0, BYTE_MAX + 1))) if draw > 0.9 else None,
                ),
            )

    return builder.build()


@pytest.fixture
def mod_samples() -> tuple[Sample, ...]:
    """Waveforms this format stores byte for byte: one channel, eight bits, an even number of frames."""
    return (
        Sample(
            name="lead",
            pcm=lattice(np.linspace(-1.0, 1.0, 32), BitDepth.EIGHT),
            rate=REFERENCE_RATE,
            depth=BitDepth.EIGHT,
        ),
        Sample(
            name="bass",
            pcm=lattice(np.linspace(1.0, -1.0, 24), BitDepth.EIGHT),
            rate=FINETUNE_RATES[3],
            depth=BitDepth.EIGHT,
            volume=48,
        ),
        Sample(
            name="looped",
            pcm=lattice(np.sin(np.linspace(0.0, 6.0, 48)), BitDepth.EIGHT),
            rate=FINETUNE_RATES[9],
            depth=BitDepth.EIGHT,
            loop=Loop(begin=8, end=40, mode=LoopMode.FORWARD),
        ),
    )


@pytest.fixture
def mod_song(mod_samples: tuple[Sample, ...]) -> Song:
    """A song this format writes and reads back unchanged, at the clock every module of it starts on."""
    return Song(
        name="trackmod",
        channels=CANONICAL_CHANNELS,
        patterns=(
            mod_pattern(channels=CANONICAL_CHANNELS, samples=len(mod_samples), seed=11),
            mod_pattern(channels=CANONICAL_CHANNELS, samples=len(mod_samples), seed=12),
        ),
        order=OrderList(entries=(0, 1, 0), restart=1),
        voices=SampleVoices(samples=mod_samples),
        playback=Playback(speed=DEFAULT_SPEED, tempo=DEFAULT_TEMPO),
    )


def sample_record(
    *,
    name: bytes = b"",
    length: int = 0,
    finetune: int = 0,
    volume: int = 0,
    loop_begin: int = 0,
    loop_length: int = 1,
) -> bytes:
    """One thirty-byte sample record, built field by field the way a tracker lays it out."""
    return name.ljust(NAME_BYTES, b"\0") + struct.pack(RECORD_FORMAT, length, finetune, volume, loop_begin, loop_length)


def raw_module(
    *,
    tag: bytes = b"M.K.",
    name: bytes = b"raw",
    records: tuple[bytes, ...] = (),
    order_count: int = 1,
    restart: int = 0,
    orders: bytes = b"\0",
    patterns: bytes = b"",
    waveforms: bytes = b"",
) -> bytes:
    """A whole module built byte by byte, so a test can state exactly what a file carries.

    Every field a reader draws back into range is reachable here: an order longer than its table, a
    restart past the order, a period no key sounds, a length no waveform follows.
    """
    slots = list(records) + [sample_record() for _ in range(SAMPLE_SLOTS - len(records))]
    table = orders.ljust(ORDER_TABLE_BYTES, b"\0")[:ORDER_TABLE_BYTES]
    return (
        name.ljust(MODULE_NAME_BYTES, b"\0")
        + b"".join(slots)
        + bytes((order_count, restart))
        + table
        + tag
        + patterns
        + waveforms
    )


def silent_pattern(*, channels: int = CANONICAL_CHANNELS) -> bytes:
    """One pattern of cells stating nothing, which is what a file holds where no channel plays."""
    return bytes(PATTERN_ROWS * channels * 4)


def cell_bytes(*, period: int = 0, sample: int = 0, command: int = 0, parameter: int = 0) -> bytes:
    """The four bytes one cell occupies, laid out the way this format splits the sample number."""
    return bytes(
        (
            (sample & 0xF0) | (period >> 8),
            period & BYTE_MAX,
            ((sample & 0x0F) << 4) | command,
            parameter,
        )
    )

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
from trackmod.spec.pitch import REFERENCE_RATE
from trackmod.spec.width import BYTE_MAX
from trackmod.trackers.amiga.spec.cells import CELL_BYTES
from trackmod.trackers.amiga.spec.periods import CANONICAL_MAX_NOTE, CANONICAL_MIN_NOTE, FINETUNE_RATES
from trackmod.trackers.amiga.spec.ranges import PATTERN_ROWS
from trackmod.trackers.amiga.spec.sizes import NAME_BYTES

RECORD_FORMAT = ">HBBHH"

SAMPLE_HIGH_MASK = 0xF0
SAMPLE_LOW_MASK = 0x0F
PERIOD_HIGH_BITS = 8
SAMPLE_SHIFT = 4


def amiga_pattern(*, channels: int, samples: int, seed: int) -> Pattern:
    """A grid inside the keys this lineage tabulates, covering the columns one of its cells carries."""
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


def sample_record(
    *,
    name: bytes = b"",
    length: int = 0,
    finetune: int = 0,
    volume: int = 0,
    loop_begin: int = 0,
    loop_length: int = 1,
) -> bytes:
    """One thirty-byte sample record, built field by field the way a tracker of this lineage lays it out."""
    return name.ljust(NAME_BYTES, b"\0") + struct.pack(RECORD_FORMAT, length, finetune, volume, loop_begin, loop_length)


def silent_pattern(*, channels: int) -> bytes:
    """One pattern of cells stating nothing, which is what a file holds where no channel plays."""
    return bytes(PATTERN_ROWS * channels * CELL_BYTES)


def cell_bytes(*, period: int = 0, sample: int = 0, command: int = 0, parameter: int = 0) -> bytes:
    """The four bytes one cell occupies, laid out the way this lineage splits the sample number."""
    return bytes(
        (
            (sample & SAMPLE_HIGH_MASK) | (period >> PERIOD_HIGH_BITS),
            period & BYTE_MAX,
            ((sample & SAMPLE_LOW_MASK) << SAMPLE_SHIFT) | command,
            parameter,
        )
    )


def lineage_samples() -> tuple[Sample, ...]:
    """Waveforms this lineage stores byte for byte: one channel, eight bits, an even number of frames."""
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
def amiga_samples() -> tuple[Sample, ...]:
    """The lineage's waveforms, for the tests of the records that store them."""
    return lineage_samples()

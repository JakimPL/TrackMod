import struct
from collections.abc import Sequence

import numpy as np
import pytest

from tests.conftest import lattice
from trackmod.core.effects.effect import Effect
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.grid import Pattern
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import SampleVoices
from trackmod.spec.pitch import RATE_NOTE, REFERENCE_RATE
from trackmod.spec.width import BYTE_MAX
from trackmod.trackers.s3m.channels import channel_table
from trackmod.trackers.s3m.spec.cells import CellMask, NoteByte
from trackmod.trackers.s3m.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.s3m.spec.flags import PANNING_TABLE, RecordType
from trackmod.trackers.s3m.spec.identity import (
    END_OF_TEXT,
    MAGIC_MODULE,
    MAGIC_SAMPLE,
    MODULE_TYPE,
    UNSIGNED_FRAMES,
)
from trackmod.trackers.s3m.spec.keys import CANONICAL_MAX_NOTE, CANONICAL_MIN_NOTE
from trackmod.trackers.s3m.spec.ranges import PATTERN_ROWS
from trackmod.trackers.s3m.spec.sizes import (
    CHANNELS_STORED,
    FILE_HEADER_BYTES,
    INSTRUMENT_RECORD_BYTES,
    NAME_BYTES,
    PARAGRAPH_BYTES,
)

S3M_CHANNELS = 4
REFERENCE_KEY = Note(RATE_NOTE)
REFERENCE_BYTE = 0x40  # the byte this format spells that key with: the fourth octave, its first semitone


def s3m_pattern(*, channels: int, samples: int, seed: int) -> Pattern:
    """A grid inside the keys this format spells, covering every column a cell here carries."""
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
                    volume=int(rng.integers(0, 65)) if draw > 0.5 else None,
                    effect=Effect(command=1, parameter=int(rng.integers(0, BYTE_MAX + 1))) if draw > 0.9 else None,
                ),
            )

    return builder.build()


@pytest.fixture
def s3m_samples() -> tuple[Sample, ...]:
    """Waveforms this format stores frame for frame, across the depths and channel counts it holds."""
    return (
        Sample(name="lead", pcm=lattice(np.linspace(-1.0, 1.0, 32)), rate=REFERENCE_RATE),
        Sample(name="bass", pcm=lattice(np.linspace(1.0, -1.0, 24)), rate=22050, volume=48),
        Sample(
            name="looped",
            pcm=lattice(np.sin(np.linspace(0.0, 6.0, 48))),
            rate=44100,
            loop=Loop(begin=8, end=40, mode=LoopMode.FORWARD),
        ),
    )


@pytest.fixture
def s3m_song(s3m_samples: tuple[Sample, ...]) -> Song:
    """A song this format writes and reads back unchanged, at the clock its own tracker starts on."""
    return Song(
        name="trackmod",
        channels=S3M_CHANNELS,
        patterns=(
            s3m_pattern(channels=S3M_CHANNELS, samples=len(s3m_samples), seed=21),
            s3m_pattern(channels=S3M_CHANNELS, samples=len(s3m_samples), seed=22),
        ),
        order=OrderList(entries=(0, 1, 0)),
        voices=SampleVoices(samples=s3m_samples),
        playback=Playback(speed=DEFAULT_SPEED, tempo=DEFAULT_TEMPO),
    )


def point_at(record: bytearray, paragraph: int) -> None:
    """Write into a record the paragraph its waveform opens on, which is a third byte above a word."""
    record[13] = paragraph >> 16
    struct.pack_into("<H", record, 14, paragraph & 0xFFFF)


def instrument_record(
    *,
    kind: int = int(RecordType.SAMPLE),
    name: bytes = b"",
    filename: bytes = b"",
    paragraph: int = 0,
    length: int = 0,
    loop_begin: int = 0,
    loop_end: int = 0,
    volume: int = 64,
    pack: int = 0,
    flags: int = 0,
    c2spd: int = REFERENCE_RATE,
    magic: bytes = MAGIC_SAMPLE,
) -> bytes:
    """One eighty-byte instrument record, built field by field the way a tracker lays it out."""
    record = bytearray(INSTRUMENT_RECORD_BYTES)
    record[0] = kind
    record[1 : 1 + len(filename)] = filename
    point_at(record, paragraph)
    struct.pack_into("<III", record, 16, length, loop_begin, loop_end)
    record[28] = volume
    record[30] = pack
    record[31] = flags
    struct.pack_into("<I", record, 32, c2spd)
    record[48 : 48 + len(name)] = name
    record[76:80] = magic
    return bytes(record)


def cell_bytes(
    channel: int,
    *,
    note: int | None = None,
    sample: int = 0,
    volume: int | None = None,
    command: int | None = None,
    parameter: int = 0,
) -> bytes:
    """The marker and the groups of bytes one packed cell occupies."""
    marker = channel
    payload = bytearray()
    if note is not None:
        marker |= CellMask.KEY
        payload += bytes((note, sample))

    if volume is not None:
        marker |= CellMask.VOLUME
        payload.append(volume)

    if command is not None:
        marker |= CellMask.EFFECT
        payload += bytes((command, parameter))

    return bytes((marker, *payload))


def pattern_block(rows: Sequence[bytes]) -> bytes:
    """One pattern block: the length of the whole block, then each row closed by its terminator."""
    stream = b"".join(row + b"\x00" for row in rows)
    stream += b"\x00" * (PATTERN_ROWS - len(rows))
    return struct.pack("<H", len(stream) + 2) + stream


def silent_block() -> bytes:
    """A pattern block whose every row states nothing, which is what silence costs here."""
    return pattern_block(())


def raw_module(
    *,
    name: bytes = b"raw",
    orders: bytes = b"\x00",
    records: Sequence[bytes] = (),
    patterns: Sequence[bytes | None] = (),
    waveforms: Sequence[bytes] = (),
    channels: int = S3M_CHANNELS,
    speed: int = DEFAULT_SPEED,
    tempo: int = DEFAULT_TEMPO,
    global_volume: int = 64,
    mix_volume: int = 0xB0,
    panning: bytes | None = None,
    magic: bytes = MAGIC_MODULE,
    flags: int = 0,
    created_with: int = 0x1320,
) -> bytes:
    """A whole module built byte by byte, so a test can state exactly what a file carries.

    Every block lands on the paragraph its own pointer names, which is what a reader follows, so the
    padding is worked out here the way a writer works it out. A record names its waveform the same way,
    and where that paragraph falls is something only the whole file knows, so each record is pointed at
    the waveform passed alongside it.
    """
    header = bytearray(FILE_HEADER_BYTES)
    header[:NAME_BYTES] = name.ljust(NAME_BYTES, b"\0")[:NAME_BYTES]
    header[28] = END_OF_TEXT
    header[29] = MODULE_TYPE
    struct.pack_into(
        "<HHHHHH", header, 32, len(orders), len(records), len(patterns), flags, created_with, UNSIGNED_FRAMES
    )
    header[44:48] = magic
    header[48], header[49], header[50], header[51] = global_volume, speed, tempo, mix_volume
    header[53] = PANNING_TABLE if panning is not None else 0
    header[64:96] = bytes(channel_table(channels))

    tables = bytearray(header + orders)
    pointers = len(tables) + 2 * (len(records) + len(patterns)) + (CHANNELS_STORED if panning is not None else 0)
    at = -(-pointers // PARAGRAPH_BYTES) * PARAGRAPH_BYTES
    blocks: list[tuple[int, bytes]] = []
    record_at = at
    at = record_at + INSTRUMENT_RECORD_BYTES * len(records)
    pattern_at = []
    for block in patterns:
        if block is None:
            pattern_at.append(0)
            continue

        pattern_at.append(at)
        blocks.append((at, block))
        at = -(-(at + len(block)) // PARAGRAPH_BYTES) * PARAGRAPH_BYTES

    waveform_at = []
    for waveform in waveforms:
        waveform_at.append(at)
        blocks.append((at, waveform))
        at = -(-(at + len(waveform)) // PARAGRAPH_BYTES) * PARAGRAPH_BYTES

    slots = [bytearray(record) for record in records]
    for slot, offset in zip(slots, waveform_at):
        point_at(slot, offset // PARAGRAPH_BYTES)

    for index, slot in enumerate(slots):
        blocks.append((record_at + INSTRUMENT_RECORD_BYTES * index, bytes(slot)))

    blocks.sort()
    for index in range(len(records)):
        tables += struct.pack("<H", (record_at + INSTRUMENT_RECORD_BYTES * index) // PARAGRAPH_BYTES)

    for offset in pattern_at:
        tables += struct.pack("<H", offset // PARAGRAPH_BYTES)

    if panning is not None:
        tables += panning.ljust(CHANNELS_STORED, b"\0")[:CHANNELS_STORED]

    out = bytearray(tables)
    for offset, block in blocks:
        out += bytes(offset - len(out)) + block

    return bytes(out)


ABSENT_NOTE = int(NoteByte.ABSENT)

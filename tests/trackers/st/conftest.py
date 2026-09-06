import pytest

from tests.trackers.amiga.conftest import amiga_pattern, lineage_samples, sample_record
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import SampleVoices
from trackmod.trackers.amiga.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.amiga.spec.sizes import MODULE_NAME_BYTES, ORDER_TABLE_BYTES
from trackmod.trackers.st.spec.defaults import DEFAULT_TEMPO_BYTE
from trackmod.trackers.st.spec.ranges import CHANNELS
from trackmod.trackers.st.spec.sizes import SAMPLE_SLOTS


@pytest.fixture
def st_samples() -> tuple[Sample, ...]:
    """The lineage's waveforms, which this format stores byte for byte."""
    return lineage_samples()


@pytest.fixture
def st_song(st_samples: tuple[Sample, ...]) -> Song:
    """A song this format writes and reads back unchanged, at the clock every module of it starts on."""
    return Song(
        name="trackmod",
        channels=CHANNELS,
        patterns=(
            amiga_pattern(channels=CHANNELS, samples=len(st_samples), seed=11),
            amiga_pattern(channels=CHANNELS, samples=len(st_samples), seed=12),
        ),
        order=OrderList(entries=(0, 1, 0)),
        voices=SampleVoices(samples=st_samples),
        playback=Playback(speed=DEFAULT_SPEED, tempo=DEFAULT_TEMPO),
    )


def raw_module(
    *,
    name: bytes = b"raw",
    records: tuple[bytes, ...] = (),
    order_count: int = 1,
    tempo: int = DEFAULT_TEMPO_BYTE,
    orders: bytes = b"\0",
    patterns: bytes = b"",
    waveforms: bytes = b"",
) -> bytes:
    """A whole module built byte by byte, so a test can state exactly what a file carries.

    The header runs to six hundred bytes and states no tag, which is what a reader of this format has to
    tell it apart from the one that came after it.
    """
    slots = list(records) + [sample_record() for _ in range(SAMPLE_SLOTS - len(records))]
    table = orders.ljust(ORDER_TABLE_BYTES, b"\0")[:ORDER_TABLE_BYTES]
    return (
        name.ljust(MODULE_NAME_BYTES, b"\0")
        + b"".join(slots)
        + bytes((order_count, tempo))
        + table
        + patterns
        + waveforms
    )

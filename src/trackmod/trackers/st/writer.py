from collections.abc import Sequence

from trackmod.binary.text import encode_name
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.song import Song
from trackmod.core.voices.convert import sampled
from trackmod.spec.width import BYTE_MAX
from trackmod.trackers.amiga.layout.file import MODULE_NAME
from trackmod.trackers.amiga.patterns.packer import pack_pattern
from trackmod.trackers.amiga.samples.writer import empty_header, sample_bytes, sample_header
from trackmod.trackers.amiga.spec.sizes import MODULE_NAME_BYTES, ORDER_TABLE_BYTES
from trackmod.trackers.st.layout.file import SEQUENCE
from trackmod.trackers.st.settings import STSettings
from trackmod.trackers.st.spec.defaults import DEFAULT_TEMPO_BYTE
from trackmod.trackers.st.spec.ranges import LOOP_BEGIN_UNIT, NO_RESTART
from trackmod.trackers.st.spec.sizes import SAMPLE_SLOTS


def reject_restart(order: OrderList) -> None:
    """Refuse an order list this format has no field for.

    Raises:
        ValueError: when the song resumes anywhere but its first position, which this format's header
            keeps no byte for — Amiga ProTracker is where that byte arrived.
    """
    if order.restart != NO_RESTART:
        raise ValueError(f"the song resumes at position {order.restart}, and this format's header states no restart")


def sample_table(samples: Sequence[Sample]) -> bytes:
    """Every sample record a module writes, which is the same fifteen however few a song fills."""
    records = [sample_header(sample, begin_unit=LOOP_BEGIN_UNIT) for sample in samples]
    return b"".join(records) + empty_header() * (SAMPLE_SLOTS - len(records))


def order_table(order: OrderList) -> bytes:
    """The order table, which this format always writes at its full width whatever the song plays."""
    entries = bytes(entry & BYTE_MAX for entry in order.entries)
    return entries + bytes(ORDER_TABLE_BYTES - len(entries))


def stated_tempo(settings: STSettings) -> int:
    """The byte the header states after its order count, which is the one a file held where it held one."""
    return DEFAULT_TEMPO_BYTE if settings.tempo is None else settings.tempo


def sequence(song: Song, settings: STSettings) -> bytes:
    """Serialise the block that closes the header: how far the order runs, the speed byte, and the order."""
    return SEQUENCE.pack(
        {
            "order_count": song.order.length,
            "tempo": stated_tempo(settings),
            "orders": order_table(song.order),
        }
    )


def write_module(song: Song, settings: STSettings) -> bytes:
    """Serialise a song and its settings as a whole fifteen-sample Soundtracker file.

    The header is a fixed slab of a known length, so everything after it is found by walking what came
    before: every pattern at its fixed size, then every waveform in the order its record was written.
    """
    voices = sampled(song)
    reject_restart(song.order)
    out = bytearray(MODULE_NAME.pack({"name": encode_name(song.name, MODULE_NAME_BYTES)}))
    out += sample_table(voices.samples)
    out += sequence(song, settings)
    for pattern in song.patterns:
        out += pack_pattern(pattern)

    for sample in voices.samples:
        out += sample_bytes(sample)

    return bytes(out)

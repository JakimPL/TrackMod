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
from trackmod.trackers.mod.dialect import Dialect
from trackmod.trackers.mod.layout.file import SEQUENCE
from trackmod.trackers.mod.settings import MODSettings
from trackmod.trackers.mod.spec.ranges import LOOP_BEGIN_UNIT
from trackmod.trackers.mod.spec.sizes import SAMPLE_SLOTS
from trackmod.trackers.mod.tag import chosen


def written_dialect(song: Song, settings: MODSettings) -> Dialect:
    """The dialect a song is written under, which is the one its settings name or the one its width picks.

    Raises:
        ValueError: when the settings name a dialect of another width than the song holds.
    """
    stated = settings.dialect
    if stated is None:
        return chosen(channels=song.channels, patterns=len(song.patterns))

    if stated.channels != song.channels:
        raise ValueError(
            f"the tag {stated.tag!r} states {stated.channels} channels, and the song holds {song.channels}"
        )

    return stated


def sample_table(samples: Sequence[Sample]) -> bytes:
    """Every sample record a module writes, which is the same thirty-one however few a song fills."""
    records = [sample_header(sample, begin_unit=LOOP_BEGIN_UNIT) for sample in samples]
    return b"".join(records) + empty_header() * (SAMPLE_SLOTS - len(records))


def order_table(order: OrderList) -> bytes:
    """The order table, which this format always writes at its full width whatever the song plays."""
    entries = bytes(entry & BYTE_MAX for entry in order.entries)
    return entries + bytes(ORDER_TABLE_BYTES - len(entries))


def stated_restart(song: Song, settings: MODSettings) -> int:
    """The byte the header states a restart in, which is the one a file held where it held one."""
    return song.order.restart if settings.restart is None else settings.restart


def sequence(song: Song, settings: MODSettings, dialect: Dialect) -> bytes:
    """Serialise the block that closes the header: how far the order runs, the order itself, and the tag."""
    return SEQUENCE.pack(
        {
            "order_count": song.order.length,
            "restart": stated_restart(song, settings),
            "orders": order_table(song.order),
            "tag": dialect.tag,
        }
    )


def write_module(song: Song, settings: MODSettings) -> bytes:
    """Serialise a song and its settings as a whole Amiga ProTracker file.

    The header is a fixed slab of a known length, so everything after it is found by walking what came
    before: every pattern at its fixed size, then every waveform in the order its record was written.
    """
    voices = sampled(song)
    out = bytearray(MODULE_NAME.pack({"name": encode_name(song.name, MODULE_NAME_BYTES)}))
    out += sample_table(voices.samples)
    out += sequence(song, settings, written_dialect(song, settings))
    for pattern in song.patterns:
        out += pack_pattern(pattern)

    for sample in voices.samples:
        out += sample_bytes(sample)

    return bytes(out)

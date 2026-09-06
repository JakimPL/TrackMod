import struct
from collections.abc import Sequence
from typing import Final

from trackmod.binary.text import encode_name
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.song import Song
from trackmod.core.voices.convert import sampled
from trackmod.trackers.s3m.channels import channel_table, stated_width
from trackmod.trackers.s3m.layout.file import FILE_HEADER
from trackmod.trackers.s3m.panning import stored_panning
from trackmod.trackers.s3m.parapointers import parapointer
from trackmod.trackers.s3m.patterns.packer import pack_pattern
from trackmod.trackers.s3m.placement import Placement, aligned
from trackmod.trackers.s3m.samples.writer import sample_bytes, sample_record
from trackmod.trackers.s3m.settings import S3MSettings
from trackmod.trackers.s3m.spec.flags import (
    MIX_VOLUME_MASK,
    PANNING_STATED,
    PANNING_TABLE,
    STEREO_MIXING,
)
from trackmod.trackers.s3m.spec.identity import (
    END_OF_TEXT,
    MAGIC_MODULE,
    MODULE_TYPE,
    UNSIGNED_FRAMES,
)
from trackmod.trackers.s3m.spec.sizes import (
    CHANNELS_STORED,
    NAME_BYTES,
    POINTER_CODE,
)

NO_SPECIAL: Final = 0
NO_CLICK_REMOVAL: Final = 0
UNSTATED_PANNING: Final = 0


def written_channels(song: Song, settings: S3MSettings) -> tuple[int, ...]:
    """The settings table a module writes, which is the one it carries or the one its width states.

    Raises:
        ValueError: when the settings hold a table of another width than the song plays.
    """
    stated = settings.channels
    if stated is None:
        return channel_table(song.channels)

    width = stated_width(stated)
    if width != song.channels:
        raise ValueError(f"the channel settings state {width} channels, and the song holds {song.channels}")

    return stated


def panning_entry(position: int | None) -> int:
    """The byte one channel's panning slot holds, which reserves a bit for stating a position at all."""
    return UNSTATED_PANNING if position is None else PANNING_STATED | stored_panning(position)


def panning_table(settings: S3MSettings) -> bytes:
    """The block stating where each channel opens on the stereo field.

    The block keeps its room in the file whatever a module states in it, so the header's own switch is
    what says whether the positions are there to read. A module attaching none leaves every channel on
    the side its mixer slot puts it.
    """
    stated = settings.channel_panning
    if stated is None:
        return bytes(CHANNELS_STORED)

    return bytes(panning_entry(position) for position in stated)


def stated_panning(settings: S3MSettings) -> int:
    """The switch saying whether the block that follows the tables states a position for each channel."""
    return PANNING_TABLE if settings.channel_panning is not None else UNSTATED_PANNING


def stated_mix_volume(settings: S3MSettings) -> int:
    """The mixing byte: the level in its seven low bits and the stereo switch in the one above them."""
    return (STEREO_MIXING if settings.stereo else 0) | (settings.mix_volume & MIX_VOLUME_MASK)


def file_header(song: Song, settings: S3MSettings, *, patterns: int) -> bytes:
    """Serialise the file header that opens the module, which states every count the tables hold."""
    return FILE_HEADER.pack(
        {
            "name": encode_name(song.name, NAME_BYTES),
            "end_of_text": END_OF_TEXT,
            "type": MODULE_TYPE,
            "order_count": song.order.length,
            "sample_count": len(sampled(song).samples),
            "pattern_count": patterns,
            "flags": int(settings.flags),
            "created_with": settings.created_with,
            "frame_format": UNSIGNED_FRAMES,
            "magic": MAGIC_MODULE,
            "global_volume": settings.global_volume,
            "speed": song.playback.speed,
            "tempo": song.playback.tempo,
            "mix_volume": stated_mix_volume(settings),
            "click_removal": NO_CLICK_REMOVAL,
            "default_panning": stated_panning(settings),
            "special": NO_SPECIAL,
            "channel_settings": bytes(written_channels(song, settings)),
        }
    )


def order_table(order: OrderList) -> bytes:
    """The positions a song plays, one byte each, at the length the header states them at."""
    return bytes(order.entries)


def pointer_table(offsets: Sequence[int]) -> bytes:
    """The paragraph numbers a table of pointers holds, one entry to each block it names."""
    return b"".join(struct.pack(POINTER_CODE, parapointer(offset)) for offset in offsets)


def placed(song: Song, samples: Sequence[Sample], patterns: Sequence[bytes]) -> Placement:
    """Where every block this module holds lands, read from the one place the padding is worked out."""
    return Placement.of(
        orders=song.order.length,
        patterns=[len(blob) for blob in patterns],
        waveforms=[sample.stored_bytes for sample in samples],
    )


def body(
    samples: Sequence[Sample],
    patterns: Sequence[bytes],
    *,
    placement: Placement,
    start: int,
) -> bytes:
    """Every block the pointers name, each opening on the paragraph the placement gave it.

    The waveforms are laid down last because their pointers reach furthest, and each block before them
    is padded out to the boundary the next one opens on.
    """
    out = bytearray()
    for sample, offset in zip(samples, placement.waveforms):
        out += sample_record(sample, data_offset=offset)

    for blob, offset in zip(patterns, placement.patterns):
        out += bytes(offset - start - len(out)) + blob

    for sample, offset in zip(samples, placement.waveforms):
        out += bytes(offset - start - len(out)) + sample_bytes(sample)

    return bytes(out + bytes(placement.total - start - len(out)))


def write_module(song: Song, settings: S3MSettings) -> bytes:
    """Serialise a song and its settings as a whole Scream Tracker 3 file.

    Every record, pattern and waveform is found through a table of paragraph numbers, so where each
    block lands is settled before any of them is written and the tables state what the placement
    decided.
    """
    voices = sampled(song)
    patterns = [pack_pattern(pattern) for pattern in song.patterns]
    placement = placed(song, voices.samples, patterns)

    out = bytearray(file_header(song, settings, patterns=len(patterns)))
    out += order_table(song.order)
    out += pointer_table(placement.instruments)
    out += pointer_table(placement.patterns)
    out += panning_table(settings)
    start = aligned(len(out))
    out += bytes(start - len(out))
    return bytes(out) + body(voices.samples, patterns, placement=placement, start=start)

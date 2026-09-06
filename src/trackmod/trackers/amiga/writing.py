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


def sample_table(samples: Sequence[Sample], *, slots: int, begin_unit: int) -> bytes:
    """Every sample record a module writes, which is the same count however few a song fills."""
    records = [sample_header(sample, begin_unit=begin_unit) for sample in samples]
    return b"".join(records) + empty_header() * (slots - len(records))


def order_table(order: OrderList) -> bytes:
    """The order table, which both formats always write at full width whatever the song plays."""
    entries = bytes(entry & BYTE_MAX for entry in order.entries)
    return entries + bytes(ORDER_TABLE_BYTES - len(entries))


def written_module(song: Song, *, table: bytes, sequence: bytes) -> bytes:
    """Serialise a song as a whole module of this lineage, behind the header block its format states.

    The header is a fixed slab of a known length, so everything after it is found by walking what came
    before: every pattern at its fixed size, then every waveform in the order its record was written.
    """
    voices = sampled(song)
    out = bytearray(MODULE_NAME.pack({"name": encode_name(song.name, MODULE_NAME_BYTES)}))
    out += table
    out += sequence
    for pattern in song.patterns:
        out += pack_pattern(pattern)

    for sample in voices.samples:
        out += sample_bytes(sample)

    return bytes(out)

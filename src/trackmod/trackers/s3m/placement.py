from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel

from trackmod.module.storage import padded
from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Count, Offset
from trackmod.trackers.s3m.spec.sizes import (
    CHANNELS_STORED,
    FILE_HEADER_BYTES,
    INSTRUMENT_RECORD_BYTES,
    ORDER_BYTES,
    PARAGRAPH_BYTES,
    PARAPOINTER_BYTES,
)


def aligned(offset: int) -> int:
    """The paragraph boundary at or past ``offset``, which is where the next block a pointer names sits."""
    return padded(offset, alignment=PARAGRAPH_BYTES)


def tables_bytes(*, samples: int, patterns: int, orders: int) -> int:
    """Every byte before the first record: the header, the order list, both pointer tables and the panning."""
    pointers = PARAPOINTER_BYTES * (samples + patterns)
    return FILE_HEADER_BYTES + ORDER_BYTES * orders + pointers + CHANNELS_STORED


def _laid(sizes: Sequence[int], start: int) -> tuple[tuple[int, ...], int]:
    offsets = []
    at = start
    for size in sizes:
        offsets.append(at)
        at = aligned(at + size)

    return tuple(offsets), at


class Placement(BaseModel):
    """Where every block a module's pointers name begins, and how far the whole file reaches.

    Each pointer names a paragraph, so every block opens on one and whatever came before it is padded
    out to the boundary. The order the blocks sit in is the order their pointers can reach: an
    instrument record and a pattern are named by a sixteen-bit paragraph number, and a waveform by a
    twenty-four-bit one, so the waveforms take the ground the file runs furthest over.

    One more sample therefore moves the body by its own eighty bytes and by whatever padding the shift
    changes, which is why every offset a writer states and every byte a size report counts are read from
    here and nowhere else. ``padding`` is what those boundaries cost: the ground between the last byte of
    one block and the paragraph the next one opens on.
    """

    model_config = FROZEN

    instruments: tuple[Offset, ...]
    patterns: tuple[Offset, ...]
    waveforms: tuple[Offset, ...]
    total: Count
    padding: Count

    @classmethod
    def of(
        cls,
        *,
        orders: int,
        patterns: Sequence[int],
        waveforms: Sequence[int],
    ) -> Placement:
        """Lay out a module holding one instrument record per waveform, block after block.

        ``patterns`` and ``waveforms`` state how many bytes each of those blocks occupies, which is all
        the arithmetic needs: everything else the file spends is fixed by the counts.
        """
        samples = len(waveforms)
        tables = tables_bytes(samples=samples, patterns=len(patterns), orders=orders)
        start = aligned(tables)
        records = tuple(start + INSTRUMENT_RECORD_BYTES * index for index in range(samples))
        packed, after_patterns = _laid(patterns, start + INSTRUMENT_RECORD_BYTES * samples)
        frames, total = _laid(waveforms, after_patterns)
        stated = tables + INSTRUMENT_RECORD_BYTES * samples + sum(patterns) + sum(waveforms)
        return cls(
            instruments=records,
            patterns=packed,
            waveforms=frames,
            total=total,
            padding=total - stated,
        )

from collections.abc import Sequence
from typing import Annotated, Final

from pydantic import BaseModel, Field

from trackmod.core.samples.depth import BitDepth
from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Count

NO_PADDING: Final = 1

Alignment = Annotated[int, Field(ge=NO_PADDING)]


def padded(size: int, *, alignment: int) -> int:
    """``size`` rounded up to the boundary a format lays its blocks on."""
    return -(-size // alignment) * alignment


class Storage(BaseModel):
    """What each kind of content costs a format in records, so a caller can budget before a song exists.

    A :class:`~trackmod.module.size.SizeReport` answers what a song already costs. This answers the
    question a caller asks earlier: how many bytes does one more sample, instrument or pattern add? A
    caller filling a byte budget needs that answer while it is still choosing what to store.

    Each count covers every byte the file spends on one more of that thing, the table entry it occupies
    included, so a format found through offset tables charges the entry here rather than leaving it for a
    caller to remember. ``sample`` is charged per stored **slot**: a format keeping a shared sample table
    spends it once per waveform, and a format whose instruments own their samples spends it once per
    owner.

    Each format's size model reads its own table, so the counts stated here and the bytes a writer emits
    have one home.

    ``alignment`` is the boundary each block opens on, which is what a format spends on padding: one byte
    where a file lays its content down back to back, a word where a record counts its length in pairs, a
    paragraph where a pointer names one. Every count below is rounded to it, so what a caller budgets
    covers the padding as well as the bytes.
    """

    model_config = FROZEN

    file: Count
    order: Count
    pattern: Count
    instrument: Count
    empty_instrument: Count
    sample: Count
    alignment: Alignment = NO_PADDING

    def frames_bytes(self, *, frames: int, depth: BitDepth) -> int:
        """How many bytes a waveform of ``frames`` frames occupies at one depth, padding included."""
        return padded(frames * depth.bytes_per_frame, alignment=self.alignment)

    @property
    def record_bytes(self) -> int:
        """What one more sample's own records cost, on the boundary the next block opens past them."""
        return padded(self.sample, alignment=self.alignment)

    def sample_bytes(self, *, frames: int, depth: BitDepth) -> int:
        """What one more stored sample costs: its records and its frames together, padding included.

        A format laying its content down back to back spends exactly this. A format opening every block
        on a paragraph spends this at most, because whether the record's table entry tips the tables
        onto the next boundary depends on how full they already are.
        """
        return self.record_bytes + self.frames_bytes(frames=frames, depth=depth)

    def instrument_bytes(self, *, samples: int) -> int:
        """What one instrument's own record costs, given how many stored slots it owns.

        A format reserving a short header for an instrument that owns nothing charges that instead, which
        is what makes placeholder instrument slots cheap.
        """
        return self.instrument if samples else self.empty_instrument

    def overhead(
        self,
        *,
        instruments: Sequence[int],
        samples: int,
        patterns: int,
        orders: int,
    ) -> int:
        """Every byte a module spends on records, before any waveform or packed pattern stream.

        ``instruments`` gives how many stored slots each instrument owns, which decides the header each
        one is written in. ``samples`` counts the slots the module records in total.
        """
        return (
            self.file
            + self.order * orders
            + self.pattern * patterns
            + sum(self.instrument_bytes(samples=owned) for owned in instruments)
            + self.sample * samples
        )

    def frames_budget(self, budget: int, *, depth: BitDepth) -> int:
        """The longest waveform, in frames, whose stored sample fits in ``budget`` bytes.

        The frames are counted back from the room left past the records, and only whole boundaries of it
        are room a waveform can use.
        """
        room = budget - self.record_bytes
        return max(0, room // self.alignment * self.alignment // depth.bytes_per_frame)

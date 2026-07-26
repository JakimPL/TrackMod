from collections.abc import Sequence

from pydantic import BaseModel

from trackmod.core.samples.depth import BitDepth
from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Count


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
    """

    model_config = FROZEN

    file: Count
    order: Count
    pattern: Count
    instrument: Count
    empty_instrument: Count
    sample: Count

    def frames_bytes(self, *, frames: int, depth: BitDepth) -> int:
        """How many bytes a waveform of ``frames`` frames occupies at one depth."""
        return frames * depth.bytes_per_frame

    def sample_bytes(self, *, frames: int, depth: BitDepth) -> int:
        """What one more stored sample costs: its records and its frames together."""
        return self.sample + self.frames_bytes(frames=frames, depth=depth)

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
        """The longest waveform, in frames, whose stored sample fits in ``budget`` bytes."""
        return max(0, (budget - self.sample) // depth.bytes_per_frame)

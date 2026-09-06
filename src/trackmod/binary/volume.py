from __future__ import annotations

from pydantic import BaseModel

from trackmod.core.volumes.codec import decode_volume
from trackmod.core.volumes.command import VolumeCommand, VolumeEffect, VolumeValue
from trackmod.limits.bound import Bound
from trackmod.schema.config import FROZEN
from trackmod.spec.grid import EMPTY


class VolumeSpan(BaseModel):
    """One run of a volume-column byte: what it states, where the run opens, and the amounts it holds."""

    model_config = FROZEN

    effect: VolumeEffect
    base: int
    amounts: Bound

    def holds(self, byte: int) -> bool:
        """Whether ``byte`` falls inside this run."""
        return self.amounts.contains(byte - self.base)

    def stated(self, byte: int) -> VolumeCommand:
        """The command ``byte`` states, at the amount it counts from this run's base."""
        return VolumeCommand(effect=self.effect, amount=byte - self.base)

    def stored(self, amount: int) -> int:
        """The byte this run stores ``amount`` as."""
        return self.base + amount


class VolumeColumn(BaseModel):
    """How one format divides its volume-column byte between levels and the effects it carries beside them.

    A tracker reads the column by the range a byte falls in, so stating those ranges as data is what lets
    the parser, the packer and the capacity table read one specification. ``absent`` is the byte a format
    writes where a cell states no volume at all, which the formats storing every column of a cell need.
    """

    model_config = FROZEN

    level_base: int
    levels: Bound
    spans: tuple[VolumeSpan, ...]
    absent: int | None

    def span(self, effect: VolumeEffect) -> VolumeSpan | None:
        """The run this column gives ``effect``, where it names one."""
        return next((span for span in self.spans if span.effect is effect), None)

    def states_volume(self, byte: int) -> bool:
        """Whether ``byte`` states a volume at all, apart from the byte a format writes for none."""
        return byte != self.absent

    def stated(self, byte: int) -> VolumeValue | None:
        """The level or command ``byte`` states, or ``None`` when it names nothing this column defines."""
        if not self.states_volume(byte):
            return None

        level = byte - self.level_base
        if self.levels.contains(level):
            return level

        return next((span.stated(byte) for span in self.spans if span.holds(byte)), None)

    def stored(self, volume: VolumeValue) -> int | None:
        """The byte this column stores ``volume`` as, or ``None`` when it cannot state it."""
        match volume:
            case VolumeCommand():
                span = self.span(volume.effect)
                return span.stored(volume.amount) if span is not None and span.amounts.contains(volume.amount) else None
            case int():
                return self.level_base + volume if self.levels.contains(volume) else None

    def encoded(self, volume: VolumeValue) -> int:
        """The byte this column stores ``volume`` as.

        Raises:
            ValueError: when the column cannot state ``volume``.
        """
        byte = self.stored(volume)
        if byte is None:
            raise ValueError(self.refusal(volume))

        return byte

    def stored_code(self, code: int) -> int:
        """The byte a grid volume code is written as, leaving an absent volume absent.

        Raises:
            ValueError: when the code names a volume this column cannot state.
        """
        if code == EMPTY:
            return EMPTY

        return self.encoded(decode_volume(code))

    def refusal(self, volume: VolumeValue) -> str:
        """Why this column cannot state ``volume``."""
        match volume:
            case VolumeCommand():
                span = self.span(volume.effect)
                if span is None:
                    return f"the volume column has no run for {volume.effect.name}"

                return f"amount {volume.amount} lies outside {span.amounts}, the amounts its run holds"
            case int():
                return f"level {volume} lies outside {self.levels}, the levels the volume column holds"

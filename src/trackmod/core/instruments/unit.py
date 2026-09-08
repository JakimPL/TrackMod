from __future__ import annotations

from pydantic import BaseModel, model_validator

from trackmod.core.instruments.instrument import Instrument
from trackmod.core.samples.sample import Sample
from trackmod.schema.config import FROZEN


class InstrumentUnit(BaseModel):
    """One instrument together with the samples its keymap reaches, numbered from zero.

    A song holds one flat sample table that every instrument indexes into, so an instrument on its own
    names positions that mean something only in the song it came from. Pairing it with its own samples
    makes it portable: the keymap here indexes into ``samples`` alone, and a song receiving the unit
    renumbers those positions in its own table. A unit holding no samples is a reserved slot, where the
    instrument routes no key anywhere.

    Build one with :func:`~trackmod.core.instruments.transfer.extract` or
    :func:`~trackmod.core.instruments.transfer.units`, and put units back into a song with
    :func:`~trackmod.core.instruments.transfer.combine`.

    Args:
        instrument: The instrument, with its keymap already numbered against ``samples``.
        samples: The waveforms its keys reach, in the order the keys first name them.

    Raises:
        ValidationError: when the keymap names a sample position ``samples`` does not hold.
    """

    model_config = FROZEN

    instrument: Instrument
    samples: tuple[Sample, ...]

    @model_validator(mode="after")
    def _references_resolve(self) -> InstrumentUnit:
        for sample in self.instrument.samples:
            if sample >= len(self.samples):
                raise ValueError(f"instrument {self.instrument.name!r} names sample {sample} of {len(self.samples)}")

        return self

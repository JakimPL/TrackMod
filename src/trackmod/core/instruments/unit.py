from __future__ import annotations

from pydantic import BaseModel, model_validator

from trackmod.core.instruments.instrument import Instrument
from trackmod.core.samples.sample import Sample
from trackmod.schema.config import FROZEN


class InstrumentUnit(BaseModel):
    """One instrument together with the samples its keymap reaches, numbered from zero.

    A song holds one flat sample table that every instrument indexes into, so an instrument on its own
    names positions that mean something only in the song it came from. Pairing it with its own samples
    is what makes it portable: here the keymap indexes into ``samples`` alone, and a song receiving the
    unit restates those positions in its own table.

    An instrument routing no key to a sample is a unit holding none, which is what a reserved slot is.
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

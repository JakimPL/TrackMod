from __future__ import annotations

from pydantic import BaseModel, model_validator

from trackmod.core.instruments.instrument import Instrument
from trackmod.core.samples.sample import Sample
from trackmod.schema.config import FROZEN


class SampleVoices(BaseModel):
    """The voices of a song whose instrument column names a sample, sounded at the pressed key's pitch.

    This is what Amiga ProTracker and Scream Tracker 3 hold, and what Impulse Tracker holds while its
    header leaves instruments switched off: one table, addressed directly by the cells. A key plays the
    waveform at the pitch it was pressed at, so what a voice does is decided by the sample alone.
    """

    model_config = FROZEN

    samples: tuple[Sample, ...]

    @property
    def slots(self) -> int:
        """How many values the instrument column may name."""
        return len(self.samples)


class InstrumentVoices(BaseModel):
    """The voices of a song whose instrument column names an instrument routing keys onto samples.

    This is what FastTracker 2 holds, and what Impulse Tracker holds while its header switches
    instruments on: the cells address ``instruments``, each of which carries a keymap into ``samples``
    together with the envelopes and behaviours every voice it starts follows.
    """

    model_config = FROZEN

    instruments: tuple[Instrument, ...]
    samples: tuple[Sample, ...]

    @model_validator(mode="after")
    def _references_resolve(self) -> InstrumentVoices:
        for index, instrument in enumerate(self.instruments):
            for sample in instrument.samples:
                if sample >= len(self.samples):
                    raise ValueError(f"instrument {index} names sample {sample} of {len(self.samples)}")

        return self

    @property
    def slots(self) -> int:
        """How many values the instrument column may name."""
        return len(self.instruments)


Voices = SampleVoices | InstrumentVoices

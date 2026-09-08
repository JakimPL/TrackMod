from __future__ import annotations

from pydantic import BaseModel, model_validator

from trackmod.core.instruments.instrument import Instrument
from trackmod.core.samples.sample import Sample
from trackmod.schema.config import FROZEN


class SampleVoices(BaseModel):
    """The voices of a song whose instrument column names a sample directly.

    A key plays the waveform at the pitch it was pressed at, so the sample alone decides what a voice
    does. Amiga ProTracker, Scream Tracker 3 and Soundtracker store this kind, and so does Impulse
    Tracker while its header leaves instruments switched off. Convert to the other kind with
    :func:`~trackmod.core.voices.convert.raised`.

    Args:
        samples: The waveforms, in the order the instrument column numbers them.
    """

    model_config = FROZEN

    samples: tuple[Sample, ...]

    @property
    def slots(self) -> int:
        """How many values the instrument column may name."""
        return len(self.samples)


class InstrumentVoices(BaseModel):
    """The voices of a song whose instrument column names an instrument routing keys onto samples.

    Each instrument carries a keymap into ``samples``, together with the envelopes, fadeout, levels and
    note behaviors every voice it starts follows. FastTracker 2 stores this kind, and so does Impulse
    Tracker while its header switches instruments on. Convert to the other kind with
    :func:`~trackmod.core.voices.convert.flattened`.

    Args:
        instruments: The instruments, in the order the instrument column numbers them.
        samples: The waveforms every instrument's keymap indexes into.

    Raises:
        ValidationError: when an instrument's keymap names a sample position ``samples`` does not hold.
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

import numpy as np

from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.keymap import pitched_keymap
from trackmod.core.samples.sample import Sample
from trackmod.core.voices.voices import InstrumentVoices, SampleVoices
from trackmod.spec.pitch import REFERENCE_RATE

NO_FRAMES = 0


def placeholder(name: str) -> Sample:
    """An empty slot standing where an instrument routes no key, so the numbering stays put."""
    return Sample(name=name, pcm=np.zeros(NO_FRAMES), rate=REFERENCE_RATE)


def named_sample(instrument: Instrument, samples: tuple[Sample, ...]) -> Sample:
    """The one waveform an instrument sounds, which a cell naming it plays at the key it was pressed at.

    Raises:
        ValueError: when the instrument reaches several samples, or sounds a key at another key's pitch.
    """
    reached = instrument.samples
    if len(reached) > 1:
        raise ValueError(
            f"instrument {instrument.name!r} routes keys to {len(reached)} samples, "
            "which a cell naming a sample plays one of"
        )

    for key, assignment in enumerate(instrument.keymap):
        if assignment is not None and assignment.note.value != key:
            raise ValueError(
                f"instrument {instrument.name!r} sounds key {key} at {assignment.note}, "
                "which a cell naming a sample plays at the key it presses"
            )

    return placeholder(instrument.name) if not reached else samples[reached[0]]


def flattened(voices: InstrumentVoices) -> SampleVoices:
    """The same voices as a plain sample table, addressed the way a cell naming a sample addresses it.

    Each instrument contributes the waveform its keys reach, at the position the instrument itself held,
    so every cell keeps naming the voice it named before. The routing is what travels: the envelopes,
    fadeout, levels and note behaviours an instrument carries stay behind, which is what a table of
    samples holds room for.

    Raises:
        ValueError: when an instrument reaches several samples, or sounds a key at another key's pitch.
    """
    return SampleVoices(samples=tuple(named_sample(instrument, voices.samples) for instrument in voices.instruments))


def raised(voices: SampleVoices) -> InstrumentVoices:
    """The same voices as instruments, each routing every key to one sample at that key's own pitch.

    Every cell keeps naming the voice it named before, since each sample gains the instrument sitting at
    its own position, and each new instrument sounds exactly what the sample sounded on its own.
    """
    return InstrumentVoices(
        instruments=tuple(
            Instrument(name=sample.name, keymap=pitched_keymap(sample=index))
            for index, sample in enumerate(voices.samples)
        ),
        samples=voices.samples,
    )

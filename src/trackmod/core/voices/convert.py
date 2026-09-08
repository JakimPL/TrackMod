from typing import Final

import numpy as np

from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.keymap import pitched_keymap
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import InstrumentVoices, SampleVoices
from trackmod.spec.pitch import REFERENCE_RATE

NO_FRAMES: Final = 0


def sampled(song: Song) -> SampleVoices:
    """The samples a song holds, which is what every cell of a sample-addressed format names.

    A format of that kind keeps one kind of voice: a numbered sample, sounded at the pitch of the key
    that triggers it. A song addressing instruments states the same music through :func:`flattened`,
    which keeps the waveform each instrument sounds.

    Raises:
        ValueError: when the song's cells name instruments, which such a format keeps no records for.
    """
    voices = song.voices
    if isinstance(voices, SampleVoices):
        return voices

    raise ValueError(
        f"song {song.name!r} names {len(voices.instruments)} instruments from its cells, and this format's "
        "cells name samples; flatten its voices onto samples first"
    )


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
    """Convert instruments into a plain sample table, the way a sample-addressed format stores them.

    Each instrument contributes the one waveform its keys reach, at the position the instrument itself
    held, so every cell keeps naming the voice it named before. Only the routing survives: the
    envelopes, fadeout, levels and note behaviors stay behind, because a table of samples has no room
    for them. An instrument reaching no sample at all becomes an empty placeholder slot.

    Args:
        voices: The instrument table to flatten.

    Returns:
        The same voices as samples, ready for Amiga ProTracker, Scream Tracker 3 or Soundtracker.

    Raises:
        ValueError: when an instrument reaches several samples, or plays a key at another key's pitch.
            A cell naming a sample can express neither.
    """
    return SampleVoices(samples=tuple(named_sample(instrument, voices.samples) for instrument in voices.instruments))


def raised(voices: SampleVoices) -> InstrumentVoices:
    """Convert a plain sample table into instruments, the way an instrument-addressed format stores them.

    Each sample gains an instrument at its own position, routing every key to it at that key's own
    pitch, so every cell keeps naming the voice it named before and each instrument plays what the
    sample played alone. This always succeeds, unlike :func:`flattened` in the other direction.

    Args:
        voices: The sample table to raise.

    Returns:
        The same voices as instruments, ready for FastTracker 2.

    Example:
        >>> import numpy as np
        >>> from trackmod import Sample, SampleVoices, raised
        >>> voices = SampleVoices(samples=(Sample(name="lead", pcm=np.zeros(8), rate=44100),))
        >>> len(raised(voices).instruments)
        1
    """
    return InstrumentVoices(
        instruments=tuple(
            Instrument(name=sample.name, keymap=pitched_keymap(sample=index))
            for index, sample in enumerate(voices.samples)
        ),
        samples=voices.samples,
    )

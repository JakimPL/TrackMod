from collections.abc import Sequence

from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.core.samples.sample import Sample
from trackmod.core.voices.convert import raised
from trackmod.core.voices.voices import InstrumentVoices, Voices


def extract(voices: InstrumentVoices, index: int) -> InstrumentUnit:
    """Take one instrument out of a song, together with the samples it plays.

    A keymap names positions in the song's own sample table, so an instrument alone is half a voice.
    The unit holds the other half: the samples its keys reach, renumbered from zero, in the order the
    keys first name them. Samples no key reaches are left behind.

    Args:
        voices: The song's voice table.
        index: Which instrument to take, counted from zero.

    Returns:
        The instrument and its own samples, as a portable
        :class:`~trackmod.core.instruments.unit.InstrumentUnit`.

    Raises:
        IndexError: when the table holds no instrument at that position.
    """
    instrument = voices.instruments[index]
    reached = instrument.samples
    positions = {sample: position for position, sample in enumerate(reached)}
    return InstrumentUnit(
        instrument=instrument.rerouted(positions),
        samples=tuple(voices.samples[sample] for sample in reached),
    )


def held(voices: InstrumentVoices) -> tuple[InstrumentUnit, ...]:
    """Take every instrument out of a song, each with the samples its own keymap reaches.

    Args:
        voices: The song's instrument table.

    Returns:
        One :class:`~trackmod.core.instruments.unit.InstrumentUnit` per instrument, in table order.
    """
    return tuple(extract(voices, index) for index in range(len(voices.instruments)))


def units(voices: Voices) -> tuple[InstrumentUnit, ...]:
    """Take every voice out of a song as a portable unit, whichever way the song addresses them.

    A table whose cells name samples is raised onto instruments first, so each sample arrives as an
    instrument that plays it at the pressed key's pitch. One call therefore reaches the voices of a
    module written in any of the five formats.

    Args:
        voices: The song's voice table, of either kind.

    Returns:
        One :class:`~trackmod.core.instruments.unit.InstrumentUnit` per voice, in table order.

    Example:
        >>> import numpy as np
        >>> from trackmod import Sample, SampleVoices, units
        >>> voices = SampleVoices(samples=(Sample(name="lead", pcm=np.zeros(8), rate=44100),))
        >>> len(units(voices))
        1
    """
    return held(voices if isinstance(voices, InstrumentVoices) else raised(voices))


def combine(collected: Sequence[InstrumentUnit]) -> InstrumentVoices:
    """Build one voice table from several units, renumbering each keymap against the shared samples.

    The instruments come back in the order given, and behind them the samples they reach in that same
    order, so each unit's waveforms sit in one run of the table. A unit keeps its own copy of a waveform
    even when another unit holds the same one, so every instrument plays exactly what it was extracted
    with.

    Args:
        collected: The units to place in one table, in the order they should be numbered.

    Returns:
        A table ready to pass as ``Song(voices=...)``.
    """
    instruments: list[Instrument] = []
    samples: list[Sample] = []
    for unit in collected:
        offset = len(samples)
        instruments.append(
            unit.instrument.rerouted({position: offset + position for position in range(len(unit.samples))})
        )
        samples.extend(unit.samples)

    return InstrumentVoices(instruments=tuple(instruments), samples=tuple(samples))

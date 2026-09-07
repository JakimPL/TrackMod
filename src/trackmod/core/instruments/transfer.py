from collections.abc import Sequence

from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.core.samples.sample import Sample
from trackmod.core.voices.convert import raised
from trackmod.core.voices.voices import InstrumentVoices, Voices


def extract(voices: InstrumentVoices, index: int) -> InstrumentUnit:
    """The instrument at ``index`` with the samples its keymap reaches, numbered from zero.

    The samples follow the order the keys first name them, which is the order
    :attr:`~trackmod.core.instruments.instrument.Instrument.samples` reports, so a unit lays its
    waveforms out the way the instrument reads them and carries nothing the keymap leaves untouched.

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
    """Every instrument a table holds, each with the samples its own keymap reaches.

    A song numbers its instruments in one table and its samples in another; this states the same content
    as portable units, which is what a caller reading a file for the voices inside it asks for.
    """
    return tuple(extract(voices, index) for index in range(len(voices.instruments)))


def units(voices: Voices) -> tuple[InstrumentUnit, ...]:
    """Every voice a table holds as a portable unit, whichever way the song addresses them.

    A table whose cells name samples is raised onto instruments first, so each sample arrives as the
    instrument sounding it at the pressed key's pitch. That is what lets one call reach the voices of
    every format a file may have been written in, which is what a caller reading a whole collection for
    the instruments inside it asks for.
    """
    return held(voices if isinstance(voices, InstrumentVoices) else raised(voices))


def combine(collected: Sequence[InstrumentUnit]) -> InstrumentVoices:
    """One voice table for several units, each keymap restated against the samples behind them all.

    The instruments come back in the order given and, behind them, the samples they reach in that same
    order, so each unit's waveforms sit in one run of the table. Every unit keeps its own copy of a
    waveform another one also holds, which leaves each instrument sounding exactly what it was extracted
    with.
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

from collections.abc import Sequence

from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.song import Song


def extract(song: Song, index: int) -> InstrumentUnit:
    """The instrument at ``index`` with the samples its keymap reaches, numbered from zero.

    The samples follow the order the keys first name them, which is the order
    :attr:`~trackmod.core.instruments.instrument.Instrument.samples` reports, so a unit lays its
    waveforms out the way the instrument reads them and carries nothing the keymap leaves untouched.

    Raises:
        IndexError: when the song holds no instrument at that position.
    """
    instrument = song.instruments[index]
    reached = instrument.samples
    positions = {sample: position for position, sample in enumerate(reached)}
    return InstrumentUnit(
        instrument=instrument.rerouted(positions),
        samples=tuple(song.samples[sample] for sample in reached),
    )


def combine(units: Sequence[InstrumentUnit]) -> tuple[tuple[Instrument, ...], tuple[Sample, ...]]:
    """One flat sample table for several units, each keymap restated against it.

    This is the pair a :class:`~trackmod.core.songs.song.Song` takes: the instruments in the order given
    and, behind them, the samples they reach in that same order, so each unit's waveforms sit in one run
    of the table. Every unit keeps its own copy of a waveform another one also holds, which leaves each
    instrument sounding exactly what it was extracted with.
    """
    instruments: list[Instrument] = []
    samples: list[Sample] = []
    for unit in units:
        offset = len(samples)
        instruments.append(
            unit.instrument.rerouted({position: offset + position for position in range(len(unit.samples))})
        )
        samples.extend(unit.samples)

    return tuple(instruments), tuple(samples)

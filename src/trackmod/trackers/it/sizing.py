from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.core.songs.song import Song
from trackmod.module.size import SizeReport
from trackmod.trackers.it.message import message_data
from trackmod.trackers.it.patterns.sizing import packed_bytes
from trackmod.trackers.it.settings import ITSettings
from trackmod.trackers.it.spec.sizes import INSTRUMENT_HEADER_BYTES, SAMPLE_HEADER_BYTES
from trackmod.trackers.it.spec.storage import IT_STORAGE

NO_PATTERNS = 0


def module_bytes(song: Song, settings: ITSettings) -> SizeReport:
    """How many bytes a song and its settings occupy once written as an Impulse Tracker module.

    Every record byte is read off this format's storage table, so what the table states and what the
    writer lays out answer to one another. What remains is what no table predicts: the packed cell
    streams, the waveforms, the song message the settings attach, and the blocks a later writer states
    beside the records -- names, an editing history, and whatever it appended past them all.
    """
    per_pattern = [packed_bytes(pattern) for pattern in song.patterns]
    return SizeReport(
        patterns=sum(per_pattern),
        pcm=sum(sample.stored_bytes for sample in song.samples),
        headers=IT_STORAGE.overhead(
            instruments=tuple(len(instrument.samples) for instrument in song.instruments),
            samples=len(song.samples),
            patterns=len(song.patterns),
            orders=song.order.length,
        )
        + len(message_data(settings.message))
        + settings.extensions.named_bytes
        + len(settings.extensions.appended),
        largest_pattern=max(per_pattern, default=0),
    )


def instrument_file_bytes(unit: InstrumentUnit) -> SizeReport:
    """How many bytes a unit occupies once written as a standalone Impulse Tracker instrument.

    The container holds one instrument header, one header per sample and the waveforms behind them, so
    the whole file is those three counts and the offset tables a module spends stay with the module.
    """
    return SizeReport(
        patterns=NO_PATTERNS,
        pcm=sum(sample.stored_bytes for sample in unit.samples),
        headers=INSTRUMENT_HEADER_BYTES + SAMPLE_HEADER_BYTES * len(unit.samples),
        largest_pattern=NO_PATTERNS,
    )

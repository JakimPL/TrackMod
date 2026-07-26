from trackmod.core.songs.song import Song
from trackmod.module.size import SizeReport
from trackmod.trackers.it.patterns.sizing import packed_bytes
from trackmod.trackers.it.spec.storage import IT_STORAGE


def module_bytes(song: Song) -> SizeReport:
    """How many bytes a song occupies once written as an Impulse Tracker module.

    Every record byte is read off this format's storage table, so what the table states and what the
    writer lays out answer to one another. What remains is what no table predicts: the packed cell
    streams and the waveforms.
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
        ),
        largest_pattern=max(per_pattern, default=0),
    )

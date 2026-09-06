from trackmod.core.songs.song import Song
from trackmod.core.voices.convert import sampled
from trackmod.module.size import SizeReport
from trackmod.trackers.mod.patterns.sizing import packed_bytes
from trackmod.trackers.mod.samples.writer import stored_bytes
from trackmod.trackers.mod.spec.storage import MOD_STORAGE

NO_INSTRUMENTS: tuple[int, ...] = ()


def module_bytes(song: Song) -> SizeReport:
    """How many bytes a song occupies once written as an Amiga ProTracker module.

    The header is a fixed slab: the same thirty-one sample records are written whether a song fills them
    or leaves them empty, so one more sample costs its frames and nothing else. Everything after the
    header is content, which is why the whole size is the header plus what the patterns and the
    waveforms come to.
    """
    voices = sampled(song)
    per_pattern = [packed_bytes(pattern) for pattern in song.patterns]
    return SizeReport(
        patterns=sum(per_pattern),
        pcm=sum(stored_bytes(sample) for sample in voices.samples),
        headers=MOD_STORAGE.overhead(
            instruments=NO_INSTRUMENTS,
            samples=len(voices.samples),
            patterns=len(song.patterns),
            orders=song.order.length,
        ),
        largest_pattern=max(per_pattern, default=0),
    )

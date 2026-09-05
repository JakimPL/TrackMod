from trackmod.core.songs.song import Song
from trackmod.module.size import SizeReport
from trackmod.trackers.s3m.addressing import sampled
from trackmod.trackers.s3m.patterns.sizing import block_bytes, packed_bytes
from trackmod.trackers.s3m.placement import Placement


def module_bytes(song: Song) -> SizeReport:
    """How many bytes a song occupies once written as a Scream Tracker 3 module.

    Every block sits on the paragraph its pointer names, so the padding between them is part of what a
    module costs and the layout states it: the header, the tables and every byte of padding are what the
    placement holds apart from the packed streams and the waveforms it also lays down.
    """
    voices = sampled(song)
    per_pattern = [packed_bytes(pattern) for pattern in song.patterns]
    waveforms = [sample.stored_bytes for sample in voices.samples]
    placement = Placement.of(
        orders=song.order.length,
        patterns=[block_bytes(pattern) for pattern in song.patterns],
        waveforms=waveforms,
    )
    return SizeReport(
        patterns=sum(per_pattern),
        pcm=sum(waveforms),
        headers=placement.total - sum(per_pattern) - sum(waveforms),
        largest_pattern=max(per_pattern, default=0),
    )

from trackmod.core.songs.song import Song
from trackmod.core.voices.convert import sampled
from trackmod.module.size import SizeReport
from trackmod.trackers.s3m.patterns.sizing import block_bytes, packed_bytes
from trackmod.trackers.s3m.placement import Placement
from trackmod.trackers.s3m.spec.storage import S3M_STORAGE

NO_INSTRUMENTS: tuple[int, ...] = ()


def module_placement(song: Song) -> Placement:
    """Where every block a module's pointers name lands, which is how far its tables have to reach."""
    return Placement.of(
        orders=song.order.length,
        patterns=[block_bytes(pattern) for pattern in song.patterns],
        waveforms=[sample.stored_bytes for sample in sampled(song).samples],
    )


def module_bytes(song: Song) -> SizeReport:
    """How many bytes a song occupies once written as a Scream Tracker 3 module.

    Every block sits on the paragraph its pointer names, so what a module costs is the records its
    storage table states plus the ground the boundaries between those blocks take up, which is the one
    thing the table cannot state and the placement works out.
    """
    voices = sampled(song)
    per_pattern = [packed_bytes(pattern) for pattern in song.patterns]
    waveforms = [sample.stored_bytes for sample in voices.samples]
    placement = module_placement(song)
    return SizeReport(
        patterns=sum(per_pattern),
        pcm=sum(waveforms),
        headers=S3M_STORAGE.overhead(
            instruments=NO_INSTRUMENTS,
            samples=len(voices.samples),
            patterns=len(song.patterns),
            orders=song.order.length,
        )
        + placement.padding,
        largest_pattern=max(per_pattern, default=0),
    )

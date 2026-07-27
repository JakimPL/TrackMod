from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.core.songs.song import Song
from trackmod.module.size import SizeReport
from trackmod.trackers.xm.instruments.grouping import group_samples, song_groups
from trackmod.trackers.xm.instruments.writer import waveform_bytes
from trackmod.trackers.xm.patterns.sizing import packed_bytes
from trackmod.trackers.xm.spec.sizes import (
    INSTRUMENT_FILE_HEADER_BYTES,
    SAMPLE_HEADER_BYTES,
)
from trackmod.trackers.xm.spec.storage import XM_STORAGE

NO_PATTERNS = 0


def module_bytes(song: Song) -> SizeReport:
    """How many bytes a song occupies once written as a FastTracker 2 module.

    Every instrument owns its own copy of the samples its keys reach, so a sample two instruments play is
    counted twice — which is the cost this format charges for keeping no shared sample table. Both the
    slot records and the waveforms are charged per owner, which is what the grouping reports.
    """
    groups = song_groups(song)
    per_pattern = [packed_bytes(pattern) for pattern in song.patterns]
    return SizeReport(
        patterns=sum(per_pattern),
        pcm=sum(waveform_bytes(group) for group in groups),
        headers=XM_STORAGE.overhead(
            instruments=tuple(group.length for group in groups),
            samples=sum(group.length for group in groups),
            patterns=len(song.patterns),
            orders=song.order.length,
        ),
        largest_pattern=max(per_pattern, default=0),
    )


def instrument_file_bytes(unit: InstrumentUnit) -> SizeReport:
    """How many bytes a unit occupies once written as a standalone FastTracker 2 instrument.

    The container charges for the samples the keys reach, which is what a stored instrument owns, so the
    count the grouping reports is the count the file writes headers and waveforms for.
    """
    group = group_samples(unit.instrument, unit.samples)
    return SizeReport(
        patterns=NO_PATTERNS,
        pcm=waveform_bytes(group),
        headers=INSTRUMENT_FILE_HEADER_BYTES + SAMPLE_HEADER_BYTES * group.length,
        largest_pattern=NO_PATTERNS,
    )

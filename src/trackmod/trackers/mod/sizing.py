from trackmod.core.songs.song import Song
from trackmod.module.size import SizeReport
from trackmod.trackers.amiga.sizing import module_bytes as lineage_bytes
from trackmod.trackers.mod.spec.storage import MOD_STORAGE


def module_bytes(song: Song) -> SizeReport:
    """How many bytes a song occupies once written as an Amiga ProTracker module."""
    return lineage_bytes(song, storage=MOD_STORAGE)

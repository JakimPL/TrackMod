from trackmod.core.songs.song import Song
from trackmod.module.size import SizeReport
from trackmod.trackers.amiga.sizing import module_bytes as lineage_bytes
from trackmod.trackers.st.spec.storage import ST_STORAGE


def module_bytes(song: Song) -> SizeReport:
    """How many bytes a song occupies once written as a fifteen-sample Soundtracker module."""
    return lineage_bytes(song, storage=ST_STORAGE)

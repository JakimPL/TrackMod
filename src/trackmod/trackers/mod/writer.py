from trackmod.core.songs.song import Song
from trackmod.core.voices.convert import sampled
from trackmod.trackers.amiga.writing import order_table, sample_table, written_module
from trackmod.trackers.mod.dialect import Dialect
from trackmod.trackers.mod.layout.file import SEQUENCE
from trackmod.trackers.mod.settings import MODSettings
from trackmod.trackers.mod.spec.ranges import LOOP_BEGIN_UNIT
from trackmod.trackers.mod.spec.sizes import SAMPLE_SLOTS
from trackmod.trackers.mod.tag import chosen


def written_dialect(song: Song, settings: MODSettings) -> Dialect:
    """The dialect a song is written under, which is the one its settings name or the one its width picks.

    Raises:
        ValueError: when the settings name a dialect of another width than the song holds.
    """
    stated = settings.dialect
    if stated is None:
        return chosen(channels=song.channels, patterns=len(song.patterns))

    if stated.channels != song.channels:
        raise ValueError(
            f"the tag {stated.tag!r} states {stated.channels} channels, and the song holds {song.channels}"
        )

    return stated


def stated_restart(song: Song, settings: MODSettings) -> int:
    """The byte the header states a restart in, which is the one a file held where it held one."""
    return song.order.restart if settings.restart is None else settings.restart


def sequence(song: Song, settings: MODSettings, dialect: Dialect) -> bytes:
    """Serialise the block that closes the header: how far the order runs, the order itself, and the tag."""
    return SEQUENCE.pack(
        {
            "order_count": song.order.length,
            "restart": stated_restart(song, settings),
            "orders": order_table(song.order),
            "tag": dialect.tag,
        }
    )


def write_module(song: Song, settings: MODSettings) -> bytes:
    """Serialise a song and its settings as a whole Amiga ProTracker file."""
    voices = sampled(song)
    return written_module(
        song,
        table=sample_table(voices.samples, slots=SAMPLE_SLOTS, begin_unit=LOOP_BEGIN_UNIT),
        sequence=sequence(song, settings, written_dialect(song, settings)),
    )

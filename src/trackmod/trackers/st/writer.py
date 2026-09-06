from trackmod.core.songs.order import OrderList
from trackmod.core.songs.song import Song
from trackmod.core.voices.convert import sampled
from trackmod.trackers.amiga.writing import order_table, sample_table, written_module
from trackmod.trackers.st.layout.file import SEQUENCE
from trackmod.trackers.st.settings import STSettings
from trackmod.trackers.st.spec.defaults import DEFAULT_TEMPO_BYTE
from trackmod.trackers.st.spec.ranges import LOOP_BEGIN_UNIT, NO_RESTART
from trackmod.trackers.st.spec.sizes import SAMPLE_SLOTS


def reject_restart(order: OrderList) -> None:
    """Refuse an order list this format has no field for.

    Raises:
        ValueError: when the song resumes anywhere but its first position, which this format's header
            keeps no byte for — Amiga ProTracker is where that byte arrived.
    """
    if order.restart != NO_RESTART:
        raise ValueError(f"the song resumes at position {order.restart}, and this format's header states no restart")


def stated_tempo(settings: STSettings) -> int:
    """The byte the header states after its order count, which is the one a file held where it held one."""
    return DEFAULT_TEMPO_BYTE if settings.tempo is None else settings.tempo


def sequence(song: Song, settings: STSettings) -> bytes:
    """Serialise the block that closes the header: how far the order runs, the speed byte, and the order."""
    return SEQUENCE.pack(
        {
            "order_count": song.order.length,
            "tempo": stated_tempo(settings),
            "orders": order_table(song.order),
        }
    )


def write_module(song: Song, settings: STSettings) -> bytes:
    """Serialise a song and its settings as a whole fifteen-sample Soundtracker file."""
    voices = sampled(song)
    reject_restart(song.order)
    return written_module(
        song,
        table=sample_table(voices.samples, slots=SAMPLE_SLOTS, begin_unit=LOOP_BEGIN_UNIT),
        sequence=sequence(song, settings),
    )

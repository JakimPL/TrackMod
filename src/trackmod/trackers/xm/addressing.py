from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import InstrumentVoices


def routed(song: Song) -> InstrumentVoices:
    """The instruments a song holds, which is what every cell of this format names.

    FastTracker 2 keeps one kind of voice: a numbered instrument owning the samples its keys reach. A
    song addressing samples directly states the same music through
    :func:`~trackmod.core.voices.convert.raised`, which gives each sample the instrument that sounds it.

    Raises:
        ValueError: when the song's cells name samples, which this format keeps no records for.
    """
    voices = song.voices
    if isinstance(voices, InstrumentVoices):
        return voices

    raise ValueError(
        f"song {song.name!r} names {len(voices.samples)} samples from its cells, and this format's cells "
        "name instruments; raise its voices onto instruments first"
    )

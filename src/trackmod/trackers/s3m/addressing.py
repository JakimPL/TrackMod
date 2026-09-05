from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import SampleVoices


def sampled(song: Song) -> SampleVoices:
    """The samples a song holds, which is what every cell of this format names.

    Scream Tracker 3 keeps one kind of voice: a numbered sample, sounded at the pitch of the key that
    triggers it. A song addressing instruments states the same music through
    :func:`~trackmod.core.voices.convert.flattened`, which keeps the waveform each instrument sounds.

    Raises:
        ValueError: when the song's cells name instruments, which this format keeps no records for.
    """
    voices = song.voices
    if isinstance(voices, SampleVoices):
        return voices

    raise ValueError(
        f"song {song.name!r} names {len(voices.instruments)} instruments from its cells, and this format's "
        "cells name samples; flatten its voices onto samples first"
    )

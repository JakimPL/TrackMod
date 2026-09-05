from collections.abc import Sequence

import numpy as np

from trackmod.core.patterns.grid import Pattern
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.song import Song
from trackmod.core.volumes.checks import check_volumes
from trackmod.limits.capability import Capability
from trackmod.limits.checklist import Checklist
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.spec.grid import EMPTY
from trackmod.spec.pitch import NOTE_COUNT
from trackmod.trackers.s3m.addressing import sampled
from trackmod.trackers.s3m.patterns.sizing import packed_bytes
from trackmod.trackers.s3m.settings import S3MSettings


def check_keys(checklist: Checklist, pattern: Pattern, *, subject: str) -> None:
    """Grade the lowest and the highest key a pattern plays.

    A cell spells a key as an octave over a semitone and counts its octaves from the one above the
    model's own, so the deepest keys the model numbers have no byte here — which makes how deep the
    music reaches as much a quantity as how high, and both ends worth reporting.
    """
    notes = pattern.note
    keys = notes[(notes != EMPTY) & (notes < NOTE_COUNT)]
    if not keys.size:
        return

    for key in sorted({int(np.min(keys)), int(np.max(keys))}):
        checklist.check(Capability.NOTE, key, subject=subject)


def check_song(checklist: Checklist, song: Song) -> None:
    """Grade the counts and the starting clock a song declares."""
    checklist.check(Capability.CHANNELS, song.channels, subject="song")
    checklist.check(Capability.PATTERNS, len(song.patterns), subject="song")
    checklist.check(Capability.ORDERS, song.order.length, subject="song")
    checklist.check(Capability.SAMPLES, len(sampled(song).samples), subject="song")
    checklist.check(Capability.SPEED, song.playback.speed, subject="song")
    checklist.check(Capability.TEMPO, song.playback.tempo, subject="song")


def check_patterns(checklist: Checklist, song: Song) -> None:
    """Grade each pattern's height, the stream it packs into, the keys it plays and the volumes it states."""
    for index, pattern in enumerate(song.patterns):
        subject = f"pattern {index}"
        checklist.check(Capability.PATTERN_ROWS, pattern.rows, subject=subject)
        checklist.check(Capability.PATTERN_BYTES, packed_bytes(pattern), subject=subject)
        check_keys(checklist, pattern, subject=subject)
        check_volumes(checklist, pattern, subject=subject)


def check_samples(checklist: Checklist, samples: Sequence[Sample]) -> None:
    """Grade each sample's stored length, playback rate and two volume levels."""
    for index, sample in enumerate(samples):
        subject = f"sample {index} ({sample.name!r})"
        checklist.check(Capability.SAMPLE_FRAMES, sample.stored_bytes, subject=subject)
        checklist.check(Capability.SAMPLE_RATE, sample.rate, subject=subject)
        checklist.check(Capability.SAMPLE_VOLUME, sample.volume, subject=subject)
        checklist.check(Capability.SAMPLE_GAIN, sample.gain, subject=subject)


def check_settings(checklist: Checklist, settings: S3MSettings) -> None:
    """Grade the song-wide levels this format adds."""
    checklist.check(Capability.SONG_VOLUME, settings.global_volume, subject="settings")
    checklist.check(Capability.MIX_VOLUME, settings.mix_volume, subject="settings")


def violations(song: Song, settings: S3MSettings, *, limits: Limits) -> tuple[Violation, ...]:
    """Every bound a song and its settings break, in the order the checks find them.

    This format carries no envelopes and no instrument records, so what a song states through either is
    content it has no encoding for, which raises where it is met.
    """
    checklist = Checklist(limits)
    check_song(checklist, song)
    check_patterns(checklist, song)
    check_samples(checklist, sampled(song).samples)
    check_settings(checklist, settings)
    return checklist.violations

from collections.abc import Sequence

from trackmod.core.notes.checks import check_keys
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.song import Song
from trackmod.core.voices.convert import sampled
from trackmod.limits.capability import Capability
from trackmod.limits.checklist import Checklist
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.trackers.mod.samples.writer import stored_bytes


def check_song(checklist: Checklist, song: Song) -> None:
    """Grade the counts and the starting clock a song declares.

    The clock is pinned to the one every module of this format starts on, because the header states
    none: a song asking to start anywhere else is told so, which keeps the clock it asked for visible.
    """
    checklist.check(Capability.CHANNELS, song.channels, subject="song")
    checklist.check(Capability.PATTERNS, len(song.patterns), subject="song")
    checklist.check(Capability.ORDERS, song.order.length, subject="song")
    checklist.check(Capability.SAMPLES, len(sampled(song).samples), subject="song")
    checklist.check(Capability.SPEED, song.playback.speed, subject="song")
    checklist.check(Capability.TEMPO, song.playback.tempo, subject="song")


def check_patterns(checklist: Checklist, song: Song) -> None:
    """Grade each pattern's height and the keys it plays."""
    for index, pattern in enumerate(song.patterns):
        subject = f"pattern {index}"
        checklist.check(Capability.PATTERN_ROWS, pattern.rows, subject=subject)
        check_keys(checklist, pattern, subject=subject)


def check_samples(checklist: Checklist, samples: Sequence[Sample]) -> None:
    """Grade each sample's length, playback rate and two volume levels.

    A waveform is bounded twice over, because a record states its length in pairs of bytes: the frames
    it holds, and the block those frames come to once the pair is filled.

    The rate bound is the whole of this format's tuning: sixteen rows an eighth of a semitone apart
    around the reference, so a sample recorded anywhere else is told to be resampled onto one of them.
    """
    for index, sample in enumerate(samples):
        subject = f"sample {index} ({sample.name!r})"
        checklist.check(Capability.SAMPLE_FRAMES, sample.frames, subject=subject)
        checklist.check(Capability.SAMPLE_BYTES, stored_bytes(sample), subject=subject)
        checklist.check(Capability.SAMPLE_RATE, sample.rate, subject=subject)
        checklist.check(Capability.SAMPLE_VOLUME, sample.volume, subject=subject)
        checklist.check(Capability.SAMPLE_GAIN, sample.gain, subject=subject)


def violations(song: Song, *, limits: Limits) -> tuple[Violation, ...]:
    """Every bound a song breaks, in the order the checks find them.

    This format carries no envelopes, no instrument records and no volume column, so what a song states
    through any of them is content it has no encoding for, which raises where it is met.
    """
    checklist = Checklist(limits)
    check_song(checklist, song)
    check_patterns(checklist, song)
    check_samples(checklist, sampled(song).samples)
    return checklist.violations

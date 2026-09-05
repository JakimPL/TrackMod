from collections.abc import Sequence

import numpy as np

from trackmod.core.patterns.grid import Pattern
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.song import Song
from trackmod.limits.capability import Capability
from trackmod.limits.checklist import Checklist
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.spec.grid import EMPTY
from trackmod.spec.pitch import NOTE_COUNT
from trackmod.trackers.mod.addressing import sampled
from trackmod.trackers.mod.samples.writer import stored_frames


def check_keys(checklist: Checklist, pattern: Pattern, *, subject: str) -> None:
    """Grade the lowest and the highest key a pattern plays.

    This is the one format whose key range is bounded at both ends: a cell states a period, and a period
    is twelve bits, so how deep the music reaches is as much a quantity as how high. Both ends are
    therefore worth reporting.
    """
    notes = pattern.note
    keys = notes[(notes != EMPTY) & (notes < NOTE_COUNT)]
    if not keys.size:
        return

    for key in sorted({int(np.min(keys)), int(np.max(keys))}):
        checklist.check(Capability.NOTE, key, subject=subject)


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
    """Grade each sample's stored length, playback rate and two volume levels.

    The rate bound is the whole of this format's tuning: sixteen rows an eighth of a semitone apart
    around the reference, so a sample recorded anywhere else is told to be resampled onto one of them.
    """
    for index, sample in enumerate(samples):
        subject = f"sample {index} ({sample.name!r})"
        checklist.check(Capability.SAMPLE_FRAMES, stored_frames(sample.frames), subject=subject)
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

from collections.abc import Sequence

from trackmod.core.notes.checks import check_keys
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.song import Song
from trackmod.core.voices.convert import sampled
from trackmod.core.volumes.checks import check_volumes
from trackmod.limits.capability import Capability
from trackmod.limits.checklist import Checklist
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.trackers.s3m.patterns.sizing import block_bytes
from trackmod.trackers.s3m.settings import S3MSettings
from trackmod.trackers.s3m.sizing import module_placement


def check_song(checklist: Checklist, song: Song) -> None:
    """Grade the counts and the starting clock a song declares."""
    checklist.check(Capability.CHANNELS, song.channels, subject="song")
    checklist.check(Capability.PATTERNS, len(song.patterns), subject="song")
    checklist.check(Capability.ORDERS, song.order.length, subject="song")
    checklist.check(Capability.SAMPLES, len(sampled(song).samples), subject="song")
    checklist.check(Capability.SPEED, song.playback.speed, subject="song")
    checklist.check(Capability.TEMPO, song.playback.tempo, subject="song")


def check_patterns(checklist: Checklist, song: Song) -> None:
    """Grade each pattern's height, the block it packs into, the keys it plays and the volumes it states.

    The block is what the length field states, so what is graded is the packed stream and the two bytes
    of length that open it.
    """
    for index, pattern in enumerate(song.patterns):
        subject = f"pattern {index}"
        checklist.check(Capability.PATTERN_ROWS, pattern.rows, subject=subject)
        checklist.check(Capability.PATTERN_BYTES, block_bytes(pattern), subject=subject)
        check_keys(checklist, pattern, subject=subject)
        check_volumes(checklist, pattern, subject=subject)


def check_samples(checklist: Checklist, samples: Sequence[Sample]) -> None:
    """Grade each sample's length, playback rate and two volume levels.

    A waveform is bounded twice over: the frames a record names, and the block they come to once the
    depth and the channel count are counted in, which is the ceiling the tracker's own loader states.
    """
    for index, sample in enumerate(samples):
        subject = f"sample {index} ({sample.name!r})"
        checklist.check(Capability.SAMPLE_FRAMES, sample.frames, subject=subject)
        checklist.check(Capability.SAMPLE_BYTES, sample.stored_bytes, subject=subject)
        checklist.check(Capability.SAMPLE_RATE, sample.rate, subject=subject)
        checklist.check(Capability.SAMPLE_VOLUME, sample.volume, subject=subject)
        checklist.check(Capability.SAMPLE_GAIN, sample.gain, subject=subject)


def check_placement(checklist: Checklist, song: Song) -> None:
    """Grade where the blocks this module's tables name land, which is as far as its pointers reach.

    Every block is found by the paragraph it opens on rather than by walking the file, so how large a
    module may grow is settled by how far its pointers see: the header's two tables name a paragraph in
    two bytes, and an instrument record names its waveform's in three.
    """
    placement = module_placement(song)
    named = (*placement.instruments, *placement.patterns)
    checklist.check(Capability.BLOCK_OFFSET, max(named, default=0), subject="song")
    checklist.check(Capability.SAMPLE_OFFSET, max(placement.waveforms, default=0), subject="song")


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
    check_placement(checklist, song)
    check_settings(checklist, settings)
    return checklist.violations

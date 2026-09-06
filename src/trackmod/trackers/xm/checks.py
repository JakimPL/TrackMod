from collections.abc import Sequence

from trackmod.core.envelopes.envelope import Envelope
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.core.notes.checks import check_keys
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.song import Song
from trackmod.core.volumes.checks import check_volumes
from trackmod.limits.capability import Capability
from trackmod.limits.checklist import Checklist
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.trackers.xm.addressing import routed
from trackmod.trackers.xm.patterns.sizing import packed_bytes


def check_envelope(
    checklist: Checklist,
    envelope: Envelope | None,
    *,
    subject: str,
) -> None:
    """Grade one envelope's length and every breakpoint it carries."""
    if envelope is None:
        return

    checklist.check(Capability.ENVELOPE_POINTS, envelope.length, subject=subject)
    for point in envelope.points:
        checklist.check(Capability.ENVELOPE_TICK, point.tick, subject=subject)
        checklist.check(Capability.ENVELOPE_VALUE, point.value, subject=subject)


def check_song(checklist: Checklist, song: Song) -> None:
    """Grade the counts and the starting clock a song declares."""
    instruments = routed(song).instruments
    checklist.check(Capability.CHANNELS, song.channels, subject="song")
    checklist.check(Capability.PATTERNS, len(song.patterns), subject="song")
    checklist.check(Capability.ORDERS, song.order.length, subject="song")
    checklist.check(Capability.INSTRUMENTS, len(instruments), subject="song")
    checklist.check(Capability.SAMPLES, stored_samples(instruments), subject="song")
    checklist.check(Capability.SPEED, song.playback.speed, subject="song")
    checklist.check(Capability.TEMPO, song.playback.tempo, subject="song")


def stored_samples(instruments: Sequence[Instrument]) -> int:
    """How many sample slots the file holds, which counts a shared sample once per instrument."""
    return sum(len(instrument.samples) for instrument in instruments)


def check_patterns(checklist: Checklist, song: Song) -> None:
    """Grade each pattern's height, the stream it packs into, the keys it plays and the volumes it states."""
    for index, pattern in enumerate(song.patterns):
        subject = f"pattern {index}"
        checklist.check(Capability.PATTERN_ROWS, pattern.rows, subject=subject)
        checklist.check(Capability.PATTERN_BYTES, packed_bytes(pattern), subject=subject)
        check_keys(checklist, pattern, subject=subject)
        check_volumes(checklist, pattern, subject=subject)


def check_samples(checklist: Checklist, samples: Sequence[Sample]) -> None:
    """Grade each sample's length, playback rate and two volume levels.

    A waveform is bounded twice over, because a header states its length in bytes: the frames it holds,
    and the block those frames come to at the depth they are stored in.

    The gain bound is what tells a caller this format has no per-sample multiplier: a sample asking for
    anything below full gain is reporting that the scaling has to be baked into its waveform instead.
    """
    for index, sample in enumerate(samples):
        subject = f"sample {index} ({sample.name!r})"
        checklist.check(Capability.SAMPLE_FRAMES, sample.frames, subject=subject)
        checklist.check(Capability.SAMPLE_BYTES, sample.stored_bytes, subject=subject)
        checklist.check(Capability.SAMPLE_RATE, sample.rate, subject=subject)
        checklist.check(Capability.SAMPLE_VOLUME, sample.volume, subject=subject)
        checklist.check(Capability.SAMPLE_GAIN, sample.gain, subject=subject)


def check_instruments(checklist: Checklist, instruments: Sequence[Instrument]) -> None:
    """Grade each instrument's level, fadeout, sample fan-out and envelopes."""
    for index, instrument in enumerate(instruments):
        subject = f"instrument {index} ({instrument.name!r})"
        checklist.check(Capability.INSTRUMENT_VOLUME, instrument.global_volume, subject=subject)
        checklist.check(Capability.FADEOUT, instrument.fadeout, subject=subject)
        checklist.check(Capability.SAMPLES_PER_INSTRUMENT, len(instrument.samples), subject=subject)
        check_envelope(checklist, instrument.volume_envelope, subject=subject)
        check_envelope(checklist, instrument.panning_envelope, subject=subject)


def violations(song: Song, *, limits: Limits) -> tuple[Violation, ...]:
    """Every bound a song breaks, in the order the checks find them.

    This format adds no song-wide levels of its own, so its settings carry nothing to bound and the
    whole report comes from the song.
    """
    voices = routed(song)
    checklist = Checklist(limits)
    check_song(checklist, song)
    check_patterns(checklist, song)
    check_samples(checklist, voices.samples)
    check_instruments(checklist, voices.instruments)
    return checklist.violations


def instrument_violations(unit: InstrumentUnit, *, limits: Limits) -> tuple[Violation, ...]:
    """Every bound a unit breaks when it is written on its own, in the order the checks find them.

    A file holding one instrument carries the same records a module does, so the bounds it answers to are
    the sample and instrument ones; the counts a song declares belong to the song.
    """
    checklist = Checklist(limits)
    check_samples(checklist, unit.samples)
    check_instruments(checklist, (unit.instrument,))
    return checklist.violations

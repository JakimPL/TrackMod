from collections.abc import Sequence

from trackmod.core.envelopes.envelope import Envelope
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.song import Song
from trackmod.limits.capability import Capability
from trackmod.limits.checklist import Checklist
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.trackers.it.patterns.sizing import packed_bytes
from trackmod.trackers.it.settings import ITSettings


def check_envelope(checklist: Checklist, envelope: Envelope | None, *, subject: str) -> None:
    """Grade one envelope's length and every breakpoint it carries."""
    if envelope is None:
        return

    checklist.check(Capability.ENVELOPE_POINTS, envelope.length, subject=subject)
    for point in envelope.points:
        checklist.check(Capability.ENVELOPE_TICK, point.tick, subject=subject)
        checklist.check(Capability.ENVELOPE_VALUE, point.value, subject=subject)


def check_song(checklist: Checklist, song: Song) -> None:
    """Grade the counts and the starting clock a song declares."""
    checklist.check(Capability.CHANNELS, song.channels, subject="song")
    checklist.check(Capability.PATTERNS, len(song.patterns), subject="song")
    checklist.check(Capability.ORDERS, song.order.length, subject="song")
    checklist.check(Capability.INSTRUMENTS, len(song.instruments), subject="song")
    checklist.check(Capability.SAMPLES, len(song.samples), subject="song")
    checklist.check(Capability.SPEED, song.playback.speed, subject="song")
    checklist.check(Capability.TEMPO, song.playback.tempo, subject="song")


def check_patterns(checklist: Checklist, song: Song) -> None:
    """Grade each pattern's height and the size of the stream it packs into."""
    for index, pattern in enumerate(song.patterns):
        checklist.check(Capability.PATTERN_ROWS, pattern.rows, subject=f"pattern {index}")
        checklist.check(Capability.PATTERN_BYTES, packed_bytes(pattern), subject=f"pattern {index}")


def check_samples(checklist: Checklist, samples: Sequence[Sample]) -> None:
    """Grade each sample's waveform length, playback rate and two volume levels."""
    for index, sample in enumerate(samples):
        subject = f"sample {index} ({sample.name!r})"
        checklist.check(Capability.SAMPLE_FRAMES, sample.frames, subject=subject)
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
        for envelope in (instrument.volume_envelope, instrument.panning_envelope, instrument.pitch_envelope):
            check_envelope(checklist, envelope, subject=subject)


def check_settings(checklist: Checklist, settings: ITSettings) -> None:
    """Grade the song-wide levels this format adds."""
    checklist.check(Capability.SONG_VOLUME, settings.global_volume, subject="settings")
    checklist.check(Capability.MIX_VOLUME, settings.mix_volume, subject="settings")


def violations(song: Song, settings: ITSettings, *, limits: Limits) -> tuple[Violation, ...]:
    """Every bound a song and its settings break, in the order the checks find them."""
    checklist = Checklist(limits)
    check_song(checklist, song)
    check_patterns(checklist, song)
    check_samples(checklist, song.samples)
    check_instruments(checklist, song.instruments)
    check_settings(checklist, settings)
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

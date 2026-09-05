from trackmod.core.instruments.instrument import Instrument
from trackmod.core.voices.voices import InstrumentVoices, Voices
from trackmod.trackers.it.spec.flags import HeaderFlag


def names_instruments(flags: HeaderFlag) -> bool:
    """Whether the cells of a file carrying these flags name instruments, as against naming samples.

    Impulse Tracker plays both ways and states which in one header bit, so a reader learns from the bit
    what the instrument column of every pattern means.
    """
    return bool(flags & HeaderFlag.USE_INSTRUMENTS)


def stated_flags(flags: HeaderFlag, voices: Voices) -> HeaderFlag:
    """The header flags with the instruments switch stating what the song's own cells name.

    Every other bit is carried through as the settings hold it, including the ones a later tracker
    claimed for itself, so a file read here states the same switches it arrived with.
    """
    if isinstance(voices, InstrumentVoices):
        return flags | HeaderFlag.USE_INSTRUMENTS

    return HeaderFlag(int(flags) & ~int(HeaderFlag.USE_INSTRUMENTS))


def stored_instruments(voices: Voices) -> tuple[Instrument, ...]:
    """The instrument records a file holds for these voices, which a song naming samples holds none of."""
    return voices.instruments if isinstance(voices, InstrumentVoices) else ()

from trackmod.core.instruments.fade import fade_seconds as shared_fade_seconds
from trackmod.core.instruments.fade import fade_ticks as shared_fade_ticks
from trackmod.core.instruments.fade import fadeout_value as shared_fadeout_value
from trackmod.trackers.it.spec.ranges import FADE_COUNTER


def fade_ticks(fadeout: int) -> float:
    """How many ticks a fading Impulse Tracker voice takes to reach silence."""
    return shared_fade_ticks(fadeout, counter=FADE_COUNTER)


def fade_seconds(fadeout: int, *, tempo: int) -> float:
    """How long a fading Impulse Tracker voice takes to reach silence at ``tempo``."""
    return shared_fade_seconds(fadeout, counter=FADE_COUNTER, tempo=tempo)


def fadeout_value(seconds: float, *, tempo: int) -> int:
    """The fadeout an Impulse Tracker instrument states to fade a voice out over ``seconds``."""
    return shared_fadeout_value(seconds, counter=FADE_COUNTER, tempo=tempo)

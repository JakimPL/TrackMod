import math
from typing import Final

from trackmod.core.timing.clock import tick_seconds
from trackmod.spec.levels import MIN_FADEOUT, NO_FADEOUT

SLOWEST_STEP: Final = 1


def fade_ticks(fadeout: int, *, counter: int) -> float:
    """How many ticks a fading voice takes to reach silence, counting down by ``fadeout`` a tick.

    A voice being faded carries a counter that starts full at ``counter`` and drops by ``fadeout`` every
    tick, and what remains of it scales the level the voice plays at. So the fadeout an instrument
    states is a rate, and the time it buys is ``counter / fadeout`` ticks.

    ``NO_FADEOUT`` leaves the counter full, which is a voice that keeps its level for as long as it
    sounds and reads here as a fade of unbounded length.

    Raises:
        ValueError: when ``fadeout`` runs backwards, or ``counter`` is empty.
    """
    if fadeout < MIN_FADEOUT:
        raise ValueError(f"fadeout {fadeout} is below {MIN_FADEOUT}")

    if counter < SLOWEST_STEP:
        raise ValueError(f"a fade counter holds at least {SLOWEST_STEP}, got {counter}")

    return math.inf if fadeout == NO_FADEOUT else counter / fadeout


def fade_seconds(fadeout: int, *, counter: int, tempo: int) -> float:
    """How long a fading voice takes to reach silence at ``tempo``.

    Raises:
        ValueError: when ``fadeout`` runs backwards, ``counter`` is empty, or ``tempo`` is below the
            slowest clock the shared model counts.
    """
    return fade_ticks(fadeout, counter=counter) * tick_seconds(tempo)


def fadeout_value(seconds: float, *, counter: int, tempo: int) -> int:
    """The rate an instrument states to fade a voice out over ``seconds`` at ``tempo``.

    This is the way back from :func:`fade_seconds`, for a caller that knows how long a released note
    should take to die and needs the counter step a format stores.

    Raises:
        ValueError: when ``seconds`` is at most nothing, or asks for a fade slower than the counter
            reaches. The slowest fade a format states drops its counter by one a tick, which lasts
            ``counter`` ticks, and anything slower would round to the value meaning no fade at all.
    """
    if seconds <= 0.0:
        raise ValueError(f"a fade lasts a positive time, got {seconds} seconds")

    value = round(counter * tick_seconds(tempo) / seconds)
    if value < SLOWEST_STEP:
        longest = fade_seconds(SLOWEST_STEP, counter=counter, tempo=tempo)
        raise ValueError(f"a fade of {seconds} s at tempo {tempo} is longer than the {longest} s the counter reaches")

    return value

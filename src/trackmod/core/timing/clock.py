from trackmod.spec.clock import MIN_SPEED, MIN_TEMPO, TICK_DENOMINATOR, TICK_NUMERATOR


def tick_seconds(tempo: int) -> float:
    """How long one tick lasts at ``tempo``: ``5 / (2 * tempo)`` seconds.

    The tick is the unit both formats count envelope breakpoints and note fades in, so a curve written
    for one tempo runs at another rate under a different one. Everything stating an instrument's
    behaviour in time reads a tick's length from here, which is what lets the tempo a curve was fitted at
    be named once and travel with it.

    Raises:
        ValueError: when ``tempo`` is below the slowest clock the shared model counts.
    """
    if tempo < MIN_TEMPO:
        raise ValueError(f"tempo {tempo} is below {MIN_TEMPO}")

    return TICK_NUMERATOR / (TICK_DENOMINATOR * tempo)


def row_seconds(speed: int, tempo: int) -> float:
    """How long one row lasts: ``speed`` ticks, each :func:`tick_seconds` long.

    This is :func:`~trackmod.core.timing.lattice.row_frames` asked in seconds rather than in frames, for
    a caller laying material out in time instead of fitting it to a whole-frame lattice.

    Raises:
        ValueError: when ``speed`` is below one tick a row, or ``tempo`` below the slowest clock.
    """
    if speed < MIN_SPEED:
        raise ValueError(f"speed {speed} is below {MIN_SPEED}")

    return speed * tick_seconds(tempo)


def elapsed_ticks(seconds: float, tempo: int) -> int:
    """How many whole ticks ``seconds`` spans at ``tempo``, to the nearest one.

    Raises:
        ValueError: when ``seconds`` runs backwards, or ``tempo`` is below the slowest clock.
    """
    if seconds < 0.0:
        raise ValueError(f"{seconds} seconds runs backwards")

    return round(seconds / tick_seconds(tempo))

from trackmod.spec.levels import MAX_PANNING
from trackmod.trackers.s3m.spec.ranges import PAN_MAX, POSITION_MAX


def stored_panning(panning: int) -> int:
    """Scale a position on the shared 0..255 panning range onto the sixteen a channel's table holds."""
    return round(panning * PAN_MAX / MAX_PANNING)


def shared_panning(stored: int) -> int:
    """Scale a stored sixteen-step panning position back onto the shared 0..255 range."""
    return round(stored * MAX_PANNING / PAN_MAX)


def stored_position(panning: int) -> int:
    """Scale a shared panning position onto the 0..128 range the panning effect's parameter counts in.

    A channel's stored panning and the effect that moves it mid-song count the field in different
    steps -- sixteen in the table, a hundred and twenty-nine in the parameter -- so the finer of the two
    is what a song reaches an exact position with.
    """
    return round(panning * POSITION_MAX / MAX_PANNING)

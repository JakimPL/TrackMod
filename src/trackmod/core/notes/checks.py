import numpy as np

from trackmod.core.patterns.grid import Pattern
from trackmod.limits.capability import Capability
from trackmod.limits.checklist import Checklist
from trackmod.spec.grid import EMPTY
from trackmod.spec.pitch import NOTE_COUNT


def stated_keys(pattern: Pattern) -> tuple[int, ...]:
    """The lowest and the highest key a pattern plays, one entry where a pattern plays a single key.

    A note column holds either a key or one of the commands the shared model numbers past the keyboard,
    so the keys are what this reads: a command names an action rather than a pitch, and the writer is
    what answers for it.
    """
    notes = pattern.note
    keys = notes[(notes != EMPTY) & (notes < NOTE_COUNT)]
    if not keys.size:
        return ()

    return tuple(sorted({int(np.min(keys)), int(np.max(keys))}))


def check_keys(checklist: Checklist, pattern: Pattern, *, subject: str) -> None:
    """Grade the keys a pattern plays against the keyboard a format states.

    Both ends are graded because a format states its keyboard as a range with a floor of its own: two of
    the four number their keys from above the model's lowest, which makes how deep the music reaches as
    much a quantity as how high it climbs.
    """
    for key in stated_keys(pattern):
        checklist.check(Capability.NOTE, key, subject=subject)

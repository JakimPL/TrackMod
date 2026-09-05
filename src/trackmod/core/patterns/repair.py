from collections.abc import Sequence

import numpy as np

from trackmod.core.patterns.column import Column
from trackmod.core.patterns.grid import Pattern
from trackmod.core.repairs.report import Repairs
from trackmod.spec.grid import EMPTY


def voiced_within(pattern: Pattern, *, slots: int, subject: str, repairs: Repairs) -> Pattern:
    """A pattern whose instrument column names only the voices the song holds.

    Cells outlive the voice they were written against -- a table shortened while the patterns stayed as
    they were leaves numbers behind that name nothing. Such a cell is read as stating no voice, so the
    channel carries on with the one it already plays, which is what a tracker sounds there.
    """
    named = pattern.instrument
    beyond = named >= slots
    reaching = int(np.count_nonzero(beyond))
    if reaching == 0:
        return pattern

    repairs.made(f"{reaching} cells naming a voice past the {slots} held carry their channel on", subject=subject)
    return Pattern.from_columns({**pattern.columns, Column.INSTRUMENT: np.where(beyond, EMPTY, named)})


def voiced_patterns(patterns: Sequence[Pattern], *, slots: int, repairs: Repairs) -> tuple[Pattern, ...]:
    """Every pattern naming only the voices the song holds, each reported under its own position."""
    return tuple(
        voiced_within(pattern, slots=slots, subject=f"pattern {index}", repairs=repairs)
        for index, pattern in enumerate(patterns)
    )

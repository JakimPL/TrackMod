from collections.abc import Mapping

import numpy as np

from trackmod.core.patterns.grid import Pattern
from trackmod.core.volumes.codec import decode_command
from trackmod.limits.capability import Capability
from trackmod.limits.checklist import Checklist
from trackmod.spec.volumes import LEVEL_COUNT


def stated_amounts(pattern: Pattern) -> Mapping[Capability, int]:
    """The largest amount each quantity reaches across a pattern's volume column.

    A pattern states its commands cell by cell and a format bounds each quantity once, so the largest
    amount is what says whether the column fits -- one reading per quantity however many cells carry one.
    """
    volumes = pattern.volume
    largest: dict[Capability, int] = {}
    for code in np.unique(volumes[volumes >= LEVEL_COUNT]):
        command = decode_command(int(code))
        capability = command.effect.capability
        largest[capability] = max(largest.get(capability, 0), command.amount)

    return largest


def check_volumes(checklist: Checklist, pattern: Pattern, *, subject: str) -> None:
    """Grade the volume-column commands a pattern states against the room a format leaves their amounts.

    A level is held to the column's own range where a cell is built, so what is left to grade is how far
    each command's amount reaches. The vocabulary is shared and each format states its own room, so one
    reading serves both.
    """
    for capability, amount in stated_amounts(pattern).items():
        checklist.check(capability, amount, subject=subject)

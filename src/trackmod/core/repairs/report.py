from __future__ import annotations

import warnings
from collections import defaultdict


class RepairWarning(UserWarning):
    """A value a file stated that the model holds no room for, drawn into range so the rest of it reads."""


class Repairs:
    """The repairs one parse made, gathered so one warning covers them all.

    A validator states what a well-formed song is, which is what this library writes. Files written by
    real trackers state values outside it -- an envelope loop ending before it begins, a loop reaching
    past the waveform it belongs to, an order naming a pattern the file leaves out. Reading such a file
    means drawing the value into range and saying so, which is what this gathers -- the way
    :class:`~trackmod.binary.warnings.UnnamedBytes` gathers the bytes a format leaves unnamed.

    Each repair is recorded against the subject that carried it, and repeats of one repair on one subject
    count once, so a file stating the same thing in slot after slot reports it once.
    """

    def __init__(self) -> None:
        self._made: dict[str, set[str]] = defaultdict(set)

    def made(self, repair: str, *, subject: str) -> None:
        """Record one repair and name what carried it."""
        self._made[subject].add(repair)

    @property
    def entries(self) -> tuple[tuple[str, str], ...]:
        """Every repair made, as a subject and what was done to it, in a stable order."""
        return tuple((subject, repair) for subject in sorted(self._made) for repair in sorted(self._made[subject]))

    def warn(self) -> None:
        """Report everything gathered as one warning, where anything was repaired."""
        entries = self.entries
        if not entries:
            return

        stated = "; ".join(f"{subject}: {repair}" for subject, repair in entries)
        warnings.warn(
            f"values drawn into range as the file was read: {stated}",
            RepairWarning,
            stacklevel=2,
        )

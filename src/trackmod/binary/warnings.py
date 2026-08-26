from __future__ import annotations

import warnings
from collections import defaultdict

from trackmod.core.patterns.column import Column


class UnnamedByteWarning(UserWarning):
    """A stored byte naming nothing its format defines, which the column it sits in reads as absent."""


class UnnamedBytes:
    """The bytes one parse met that name nothing the format defines, gathered so one warning covers them.

    A file reaching past what this library has a vocabulary for states it in cell after cell, so
    gathering what was met and reporting once says as much as a warning per cell would -- the way a
    :class:`~trackmod.limits.checklist.Checklist` gathers the violations of a whole module.
    """

    def __init__(self) -> None:
        self._met: dict[Column, set[int]] = defaultdict(set)

    def met(self, byte: int, *, column: Column) -> None:
        """Record a byte the column names nothing for."""
        self._met[column].add(byte)

    def warn(self) -> None:
        """Report everything gathered as one warning, where anything was met."""
        if not self._met:
            return

        stated = "; ".join(
            f"{column} {', '.join(str(byte) for byte in sorted(bytes_met))}" for column, bytes_met in self._met.items()
        )
        warnings.warn(
            f"bytes this format leaves unnamed, read as absent: {stated}",
            UnnamedByteWarning,
            stacklevel=2,
        )

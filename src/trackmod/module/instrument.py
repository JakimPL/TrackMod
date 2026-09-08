from pathlib import Path
from typing import Protocol

from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.limits.compliance import Compliance
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.module.size import SizeReport


class InstrumentFile(Protocol):
    """What every format's standalone instrument binding offers, so you can hold one alone.

    A module is a whole piece of music; a file of this kind is one voice out of it, which is what a
    producer of sampled instruments ships when the instrument rather than the piece is the product. The
    same records a module writes for an instrument and its samples make up the whole file.

    Only Impulse Tracker and FastTracker 2 store a single instrument, as ``.iti`` and ``.xi``. The
    interface mirrors :class:`~trackmod.module.protocol.TrackerModule`, so both are read the same way.

    Reading the instrument: ``unit``, ``extension``.
    Checking it: ``limits``, ``violations()``, ``reach``, ``exceeded()``, ``require_reach()``.
    Sizing it: ``size()``.
    Writing it: ``to_bytes()``, ``save()``.
    """

    @property
    def unit(self) -> InstrumentUnit:
        """The instrument this file carries, together with the samples its keymap reaches."""

    @property
    def limits(self) -> Limits:
        """The bounds this file is held to, at its compliance level.

        Returns:
            The limits for this format read at ``compliance``. They are the format's own, so an
            instrument can carry the same values here as inside a module.
        """

    @property
    def extension(self) -> str:
        """The file extension this format writes a standalone instrument with, including the leading dot."""

    def violations(self) -> tuple[Violation, ...]:
        """Every bound the unit breaks at this file's compliance level.

        Returns:
            One :class:`~trackmod.limits.violation.Violation` per value out of range, empty when the
            file is writable. This grades quantities only. Content this format has no encoding for
            reaches you at :meth:`to_bytes` instead.
        """

    @property
    def reach(self) -> Compliance | None:
        """The strictest level the unit fits inside.

        Returns:
            ``CANONICAL`` for a unit the format's own tracker accepts, ``EXTENDED`` for one needing a
            player descended from it, ``STRUCTURAL`` for one that can be stored but read faithfully by
            nothing, and ``None`` for a unit carrying a value no record layout holds.
        """

    def exceeded(self) -> tuple[Violation, ...]:
        """Every bound the unit passes at the strictest level, whatever level it is held to."""

    def require_reach(self, compliance: Compliance) -> None:
        """Refuse content that reaches past a level you are willing to accept.

        Args:
            compliance: The widest level to allow.

        Raises:
            LimitError: carrying every bound the content passes at or beyond ``compliance``.
        """

    def size(self) -> SizeReport:
        """How many bytes the file occupies, counted from the tables rather than written.

        Returns:
            A size report. ``total`` is the file length, and a file holding one instrument spends
            every byte on records and waveforms.
        """

    def to_bytes(self) -> bytes:
        """Serialize the whole file."""

    def save(self, path: Path) -> None:
        """Write the whole file to disk.

        Args:
            path: Where to write it. An existing file is overwritten.

        Raises:
            LimitError: when the unit carries values this format refuses at its compliance level.
            OSError: when the file cannot be written.
        """

from pathlib import Path
from typing import Protocol

from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.module.size import SizeReport


class InstrumentFile(Protocol):
    """The surface every format's standalone instrument binding offers, so callers can hold one alone.

    A module is a piece of music; a file of this kind is one voice out of it, which is what a producer of
    sampled instruments ships when the instrument rather than the piece is the product. The same records
    a module writes for an instrument and its samples make up the whole file.
    """

    @property
    def unit(self) -> InstrumentUnit:
        """The instrument this file carries, together with the samples its keymap reaches."""

    @property
    def limits(self) -> Limits:
        """The bounds this file is held to, at its compliance level."""

    @property
    def extension(self) -> str:
        """The file extension this format writes a standalone instrument with, including the leading dot."""

    def violations(self) -> tuple[Violation, ...]:
        """Every bound the unit breaks, empty when the file is writable."""

    def size(self) -> SizeReport:
        """How many bytes the file occupies, without serialising it."""

    def to_bytes(self) -> bytes:
        """Serialise the whole file."""

    def save(self, path: Path) -> None:
        """Serialise the file and write it to ``path``."""

from pathlib import Path
from typing import Protocol

from trackmod.core.songs.song import Song
from trackmod.limits.compliance import Compliance
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.module.size import SizeReport
from trackmod.module.storage import Storage


class TrackerModule(Protocol):
    """The surface every format binding offers, so callers can hold a module without naming its format."""

    @property
    def song(self) -> Song:
        """The format-agnostic content this module writes."""

    @property
    def limits(self) -> Limits:
        """The bounds this module is held to, at its compliance level."""

    @property
    def storage(self) -> Storage:
        """What each kind of content costs this format, for a caller budgeting before it stores anything."""

    @property
    def extension(self) -> str:
        """The file extension this format is written with, including the leading dot."""

    def violations(self) -> tuple[Violation, ...]:
        """Every bound the song breaks, empty when the module is writable."""

    @property
    def reach(self) -> Compliance:
        """The strictest level the song fits inside, which is what says who will read it back."""

    def exceeded(self) -> tuple[Violation, ...]:
        """Every bound the song passes at the strictest level, whatever level it is held to."""

    def require_reach(self, compliance: Compliance) -> None:
        """Refuse a song reaching past a level.

        Raises:
            LimitError: carrying every bound it passes at or beyond ``compliance``.
        """

    def size(self) -> SizeReport:
        """How many bytes the module occupies, without serialising it."""

    def to_bytes(self) -> bytes:
        """Serialise the whole module."""

    def save(self, path: Path) -> None:
        """Serialise the module and write it to ``path``."""

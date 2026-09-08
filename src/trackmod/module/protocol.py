from pathlib import Path
from typing import Protocol

from trackmod.core.songs.song import Song
from trackmod.limits.compliance import Compliance
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.module.provenance import Provenance
from trackmod.module.size import SizeReport
from trackmod.module.storage import Storage


class TrackerModule(Protocol):
    """What every format binding offers, so you can hold a module without naming its format.

    :func:`~trackmod.trackers.registry.load_module` returns one of these, so a loop over a mixed folder
    handles every format the same way. Name this protocol in your own signatures to accept any of the
    five.

    Reading the music: ``song``, ``provenance``, ``extension``.
    Checking it: ``limits``, ``violations()``, ``reach``, ``exceeded()``, ``require_reach()``.
    Sizing it: ``storage``, ``size()``.
    Writing it: ``to_bytes()``, ``save()``.
    """

    @property
    def song(self) -> Song:
        """The format-agnostic content this module writes."""

    @property
    def limits(self) -> Limits:
        """The bounds this module is held to, at its compliance level.

        Returns:
            The limits for this format read at ``compliance``. Ask ``limits.bound(capability)`` for
            what you may use, and ``limits.declares(capability)`` whether this format has that field
            at all.
        """

    @property
    def storage(self) -> Storage:
        """What each kind of content costs in this format, for budgeting before you store anything.

        Returns:
            The storage table: what one sample and one instrument cost, the longest waveform that
            still fits a budget, and the boundary this format's blocks start on.
        """

    @property
    def extension(self) -> str:
        """The file extension this format is written with, including the leading dot."""

    @property
    def provenance(self) -> Provenance | None:
        """What the file states about the program that wrote it, or ``None`` for a format stating none.

        A module built here carries what this library writes, and one read from a file carries what that
        file arrived with, so the answer is about the bytes rather than the song.
        """

    def violations(self) -> tuple[Violation, ...]:
        """Every bound the song breaks at this module's compliance level.

        Returns:
            One :class:`~trackmod.limits.violation.Violation` per value out of range, empty when the
            module is writable. This grades quantities only. Content this format has no encoding for
            reaches you at :meth:`to_bytes` instead.
        """

    @property
    def reach(self) -> Compliance | None:
        """The strictest level the song fits inside.

        Returns:
            ``CANONICAL`` for a song the format's own tracker accepts, ``EXTENDED`` for one needing a
            player descended from it, ``STRUCTURAL`` for one that can be stored but read faithfully by
            nothing, and ``None`` for a song carrying a value no record layout holds.
        """

    def exceeded(self) -> tuple[Violation, ...]:
        """Every bound the song passes at the strictest level, whatever level it is held to."""

    def require_reach(self, compliance: Compliance) -> None:
        """Refuse a song reaching past a level.

        Raises:
            LimitError: carrying every bound it passes at or beyond ``compliance``.
        """

    def size(self) -> SizeReport:
        """How many bytes the module occupies, counted from the tables rather than written.

        Returns:
            A size report. ``total`` is the file length, ``headers``, ``patterns`` and ``pcm`` say
            where those bytes go, and ``largest_pattern`` is what decides whether a song fits a
            format that stores a packed pattern's length in sixteen bits.
        """

    def to_bytes(self) -> bytes:
        """Serialize the whole module."""

    def save(self, path: Path) -> None:
        """Write the whole module to a file.

        Args:
            path: Where to write it. An existing file is overwritten.

        Raises:
            LimitError: when the song carries values this format refuses at its compliance level.
            ValueError: when the song carries content this format has no encoding for.
            OSError: when the file cannot be written.
        """

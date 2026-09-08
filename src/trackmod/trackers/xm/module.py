from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, model_validator

from trackmod.core.songs.song import Song
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import require
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.module.provenance import Evidence, Provenance
from trackmod.module.reaching import Reaching
from trackmod.module.size import SizeReport
from trackmod.module.storage import Storage
from trackmod.schema.config import FROZEN
from trackmod.trackers.xm.addressing import routed
from trackmod.trackers.xm.checks import violations
from trackmod.trackers.xm.limits import xm_limits
from trackmod.trackers.xm.parser import ModuleReader
from trackmod.trackers.xm.settings import XMSettings
from trackmod.trackers.xm.sizing import module_bytes
from trackmod.trackers.xm.spec.identity import EXTENSION
from trackmod.trackers.xm.spec.storage import XM_STORAGE
from trackmod.trackers.xm.writer import write_module


class XMModule(BaseModel, Reaching):
    """A FastTracker 2 module: a song, the settings this format adds, and how strictly it is held.

    Every cell of this format names an instrument, so the song it is bound to holds
    :class:`~trackmod.core.voices.voices.InstrumentVoices`. The format stores no shared sample table —
    each instrument owns copies of the samples its keys reach — so a song whose instruments share
    samples grows when written, and reading one back gives an instrument per group rather than the
    arrangement it was built from.

    Args:
        song: The music this module writes.
        compliance: How strictly it is held. See :class:`~trackmod.limits.compliance.Compliance`.
        settings: What belongs to the format rather than to the music. Defaults to what this format's
            own tracker wrote.

    Raises:
        ValidationError: when the song's cells name samples, which this format keeps no records for.
    """

    model_config = FROZEN

    song: Song
    compliance: Compliance
    settings: XMSettings = XMSettings()

    @model_validator(mode="after")
    def _cells_name_instruments(self) -> XMModule:
        routed(self.song)
        return self

    @classmethod
    def from_song(
        cls,
        song: Song,
        *,
        compliance: Compliance,
        settings: XMSettings | None = None,
    ) -> XMModule:
        """Bind a song to this format, so it can be sized, checked and written.

        Args:
            song: The music to write.
            compliance: How strictly to hold it. See :class:`~trackmod.limits.compliance.Compliance`.
            settings: This format's own settings, or ``None`` for what its own tracker wrote.

        Returns:
            The module, ready for :meth:`size`, :meth:`violations` and :meth:`save`.

        Raises:
            ValidationError: when the song's cells name samples, which this format keeps no records for
        """
        return cls(
            song=song,
            compliance=compliance,
            settings=settings or XMSettings(),
        )

    @classmethod
    def parse(
        cls,
        data: bytes,
        *,
        compliance: Compliance = Compliance.STRUCTURAL,
    ) -> XMModule:
        """Read a module from the bytes of a FastTracker 2 file.

        Args:
            data: The whole file.
            compliance: How strictly to grade the values in it. Reading defaults to
                ``Compliance.STRUCTURAL``, because a file that exists is evidence its values fit.

        Returns:
            The module, with the music at ``song`` and this format's own settings at ``settings``.

        Raises:
        ValueError: when the data does not open with this format's tag, or its header points past
            the bytes the file holds.

        Warns:
            RepairWarning: when the file holds a value the model has no room for, and it is drawn back
                into range.
            UnnamedByteWarning: when the file holds a byte this format leaves unnamed.
        """
        reader = ModuleReader(data)
        return cls(
            song=reader.song(),
            compliance=compliance,
            settings=reader.settings(),
        )

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        compliance: Compliance = Compliance.STRUCTURAL,
    ) -> XMModule:
        """Open a FastTracker 2 file and read the module inside it.

        Args:
            path: The file to read.
            compliance: How strictly to grade the values in it. Reading defaults to
                ``Compliance.STRUCTURAL``, because a file that exists is evidence its values fit.

        Returns:
            The module, with the music at ``song`` and this format's own settings at ``settings``.

        Raises:
            OSError: when the file cannot be read.
            ValueError: for everything :meth:`parse` refuses.

        Warns:
            RepairWarning: when the file holds a value the model has no room for, and it is drawn back
                into range.
            UnnamedByteWarning: when the file holds a byte this format leaves unnamed.
        """
        return cls.parse(path.read_bytes(), compliance=compliance)

    @property
    def extension(self) -> str:
        """The file extension this format is written with, including the leading dot."""
        return EXTENSION

    @property
    def provenance(self) -> Provenance:
        """What this module states about the program that wrote it.

        This format spends twenty bytes of its header on a name, so the field answers the question
        directly and the name it holds is the whole of the answer.
        """
        tracker = self.settings.tracker
        return Provenance(evidence=Evidence.NAMED, stated=tracker, tracker=tracker or None)

    @property
    def limits(self) -> Limits:
        """The bounds this module is held to, at its compliance level.

        Returns:
            The limits for this format read at ``compliance``. Ask ``limits.bound(capability)`` for
            what you may use, and ``limits.declares(capability)`` whether this format has that field
            at all.
        """
        return xm_limits(self.compliance)

    @property
    def storage(self) -> Storage:
        """What each kind of content costs in this format, for budgeting before you store anything.

        Returns:
            The storage table: what one sample and one instrument cost, the longest waveform that
            still fits a budget, and the boundary this format's blocks start on.
        """
        return XM_STORAGE

    def violations(self) -> tuple[Violation, ...]:
        """Every bound the song breaks at this module's compliance level.

        Returns:
            One :class:`~trackmod.limits.violation.Violation` per value out of range, empty when the
            module is writable. This grades quantities only. Content this format has no encoding for
            reaches you at :meth:`to_bytes` instead.
        """
        return violations(self.song, limits=self.limits)

    def exceeded(self) -> tuple[Violation, ...]:
        """Every bound the song passes at the strictest level, whatever level it is held to.

        A file read back is held to the widest level, because a file that exists is evidence its
        values were storable, so :meth:`violations` stays empty for one a later tracker wrote. This
        answers the other question: which ceilings does it pass, and whose reading does passing them
        cost?

        Returns:
            One :class:`~trackmod.limits.violation.Violation` per ceiling passed, each naming that
            ceiling through the level it broke. Empty for a song the format's own tracker accepts.
        """
        return violations(self.song, limits=xm_limits(Compliance.CANONICAL))

    def size(self) -> SizeReport:
        """How many bytes the module occupies, counted from the tables rather than written.

        Returns:
            A size report. ``total`` is the file length, ``headers``, ``patterns`` and ``pcm`` say
            where those bytes go, and ``largest_pattern`` is what decides whether a song fits a
            format that stores a packed pattern's length in sixteen bits.
        """
        return module_bytes(self.song)

    def to_bytes(self) -> bytes:
        """Write the whole module as bytes.

        A bound this format leaves room for is reported rather than raised, so a caller sees every
        problem at once. Content it has no encoding for at all — a note cut, a sustain loop, a pitch
        envelope, a volume-column effect its own column has no run for, or a keymap that transposes
        one key of a sample differently from another — is not a quantity to bound and raises where it
        is met.

        Raises:
            LimitError: when the song carries values this format refuses at its compliance level.
            ValueError: when the song carries content this format has no encoding for.

        Returns:
            The whole file, ready to write to disk or hand on.
        """
        require(self.violations())
        return write_module(self.song, self.settings)

    def save(self, path: Path) -> None:
        """Write the whole module to a file.

        Args:
            path: Where to write it. An existing file is overwritten.

        Raises:
            LimitError: when the song carries values this format refuses at its compliance level.
            ValueError: when the song carries content this format has no encoding for.
            OSError: when the file cannot be written.
        """
        path.write_bytes(self.to_bytes())

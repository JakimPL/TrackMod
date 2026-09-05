from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, model_validator

from trackmod.core.songs.song import Song
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import require
from trackmod.limits.reach import beyond, reached
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
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


class XMModule(BaseModel):
    """A FastTracker 2 module: a song, the settings this format adds, and how strictly it is held.

    Every cell of this format names an instrument, so the song it is bound to holds
    :class:`~trackmod.core.voices.voices.InstrumentVoices`. The format stores no shared sample table —
    each instrument owns copies of the samples its keys reach — so a song whose instruments share
    samples grows when written, and reading one back gives an instrument per group rather than the
    arrangement it was built from.

    Raises:
        ValueError: when the song's cells name samples, which this format keeps no records for.
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
        """Bind a song to this format at one compliance level."""
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
        """Rebuild a module from the bytes of a FastTracker 2 file.

        Raises:
            ValueError: when the data does not open with this format's tag.
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
        """Read a module from a FastTracker 2 file."""
        return cls.parse(path.read_bytes(), compliance=compliance)

    @property
    def extension(self) -> str:
        """The file extension this format is written with."""
        return EXTENSION

    @property
    def limits(self) -> Limits:
        """The bounds this module is held to, at its compliance level."""
        return xm_limits(self.compliance)

    @property
    def storage(self) -> Storage:
        """What each kind of content costs this format, for a caller budgeting before it stores anything."""
        return XM_STORAGE

    def violations(self) -> tuple[Violation, ...]:
        """Every bound the song breaks, empty when the module is writable."""
        return violations(self.song, limits=self.limits)

    def exceeded(self) -> tuple[Violation, ...]:
        """Every bound the song passes at the strictest level, whatever level it is held to.

        A file read back is held to the widest level, because a file that exists is evidence its values
        were storable, so :meth:`violations` stays empty for one a later tracker wrote. This answers the
        other question: which ceilings does it pass, and whose reading does passing them cost? Each
        violation names the ceiling through its severity.
        """
        return violations(self.song, limits=xm_limits(Compliance.CANONICAL))

    @property
    def reach(self) -> Compliance:
        """The strictest level the song fits inside, which is what says who will read it back."""
        return reached(self.exceeded())

    def require_reach(self, compliance: Compliance) -> None:
        """Refuse a song reaching past a level.

        Raises:
            LimitError: carrying every bound it passes at or beyond ``compliance``.
        """
        require(beyond(self.exceeded(), compliance))

    def size(self) -> SizeReport:
        """How many bytes the module occupies, without serialising it."""
        return module_bytes(self.song)

    def to_bytes(self) -> bytes:
        """Serialise the whole module.

        A bound this format leaves room for is reported rather than raised, so a caller sees every
        problem at once. Content it has no encoding for at all — a note cut, a sustain loop, a pitch
        envelope, a volume-column effect its own column has no run for, or a keymap that transposes
        one key of a sample differently from another — is not a quantity to bound and raises where it
        is met.

        Raises:
            LimitError: when the song carries values this format refuses at its compliance level.
            ValueError: when the song carries content this format has no encoding for.
        """
        require(self.violations())
        return write_module(self.song, self.settings)

    def save(self, path: Path) -> None:
        """Serialise the module and write it to ``path``."""
        path.write_bytes(self.to_bytes())

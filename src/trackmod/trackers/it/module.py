from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from trackmod.core.songs.song import Song
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import require
from trackmod.limits.reach import beyond, reached
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.module.size import SizeReport
from trackmod.module.storage import Storage
from trackmod.schema.config import FROZEN
from trackmod.trackers.it.checks import violations
from trackmod.trackers.it.limits import it_limits
from trackmod.trackers.it.parser import ModuleReader
from trackmod.trackers.it.settings import ITSettings
from trackmod.trackers.it.sizing import module_bytes
from trackmod.trackers.it.spec.identity import EXTENSION
from trackmod.trackers.it.spec.storage import IT_STORAGE
from trackmod.trackers.it.writer import write_module


class ITModule(BaseModel):
    """An Impulse Tracker module: a song, the settings this format adds, and how strictly it is held."""

    model_config = FROZEN

    song: Song
    compliance: Compliance
    settings: ITSettings = ITSettings()

    @classmethod
    def from_song(
        cls,
        song: Song,
        *,
        compliance: Compliance,
        settings: ITSettings | None = None,
    ) -> ITModule:
        """Bind a song to this format at one compliance level."""
        return cls(
            song=song,
            compliance=compliance,
            settings=settings or ITSettings(),
        )

    @classmethod
    def parse(
        cls,
        data: bytes,
        *,
        compliance: Compliance = Compliance.STRUCTURAL,
    ) -> ITModule:
        """Rebuild a module from the bytes of an Impulse Tracker file.

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
    ) -> ITModule:
        """Read a module from an Impulse Tracker file."""
        return cls.parse(path.read_bytes(), compliance=compliance)

    @property
    def extension(self) -> str:
        """The file extension this format is written with."""
        return EXTENSION

    @property
    def limits(self) -> Limits:
        """The bounds this module is held to, at its compliance level."""
        return it_limits(self.compliance)

    @property
    def storage(self) -> Storage:
        """What each kind of content costs this format, for a caller budgeting before it stores anything."""
        return IT_STORAGE

    def violations(self) -> tuple[Violation, ...]:
        """Every bound the song breaks, empty when the module is writable."""
        return violations(self.song, self.settings, limits=self.limits)

    def exceeded(self) -> tuple[Violation, ...]:
        """Every bound the song passes at the strictest level, whatever level it is held to.

        A file read back is held to the widest level, because a file that exists is evidence its values
        were storable, so :meth:`violations` stays empty for one a later tracker wrote. This answers the
        other question: which ceilings does it pass, and whose reading does passing them cost? Each
        violation names the ceiling through its severity.
        """
        return violations(self.song, self.settings, limits=it_limits(Compliance.CANONICAL))

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
        return module_bytes(self.song, self.settings)

    def to_bytes(self) -> bytes:
        """Serialise the whole module.

        A bound this format leaves room for is reported rather than raised, so a caller sees every
        problem at once. Content it has no encoding for at all — a volume-column effect its own column
        has no run for — is not a quantity to bound and raises where it is met.

        Raises:
            LimitError: when the song carries values this format refuses at its compliance level.
            ValueError: when the song carries content this format has no encoding for.
        """
        require(self.violations())
        return write_module(self.song, self.settings)

    def save(self, path: Path) -> None:
        """Serialise the module and write it to ``path``."""
        path.write_bytes(self.to_bytes())

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
from trackmod.trackers.mod.addressing import sampled
from trackmod.trackers.mod.checks import violations
from trackmod.trackers.mod.limits import mod_limits
from trackmod.trackers.mod.parser import ModuleReader
from trackmod.trackers.mod.settings import MODSettings
from trackmod.trackers.mod.sizing import module_bytes
from trackmod.trackers.mod.spec.identity import EXTENSION
from trackmod.trackers.mod.spec.storage import MOD_STORAGE
from trackmod.trackers.mod.writer import write_module


class MODModule(BaseModel):
    """An Amiga ProTracker module: a song, the settings this format adds, and how strictly it is held.

    Every cell of this format names a sample, so the song it is bound to holds
    :class:`~trackmod.core.voices.voices.SampleVoices`: a key plays a stored waveform at the pitch it
    was pressed at, and what a voice does is decided by the sample alone. The header states no clock,
    no instrument records and no volume column, so a song reaching for any of them is told where the
    music has to go instead.

    Raises:
        ValueError: when the song's cells name instruments, which this format keeps no records for.
    """

    model_config = FROZEN

    song: Song
    compliance: Compliance
    settings: MODSettings = MODSettings()

    @model_validator(mode="after")
    def _cells_name_samples(self) -> MODModule:
        sampled(self.song)
        return self

    @classmethod
    def from_song(
        cls,
        song: Song,
        *,
        compliance: Compliance,
        settings: MODSettings | None = None,
    ) -> MODModule:
        """Bind a song to this format at one compliance level."""
        return cls(
            song=song,
            compliance=compliance,
            settings=settings or MODSettings(),
        )

    @classmethod
    def parse(
        cls,
        data: bytes,
        *,
        compliance: Compliance = Compliance.STRUCTURAL,
    ) -> MODModule:
        """Rebuild a module from the bytes of an Amiga ProTracker file.

        Raises:
            ValueError: when the data carries no tag this format reads patterns under.
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
    ) -> MODModule:
        """Read a module from an Amiga ProTracker file."""
        return cls.parse(path.read_bytes(), compliance=compliance)

    @property
    def extension(self) -> str:
        """The file extension this format is written with."""
        return EXTENSION

    @property
    def limits(self) -> Limits:
        """The bounds this module is held to, at its compliance level."""
        return mod_limits(self.compliance)

    @property
    def storage(self) -> Storage:
        """What each kind of content costs this format, for a caller budgeting before it stores anything."""
        return MOD_STORAGE

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
        return violations(self.song, limits=mod_limits(Compliance.CANONICAL))

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
        problem at once. Content it has no encoding for at all — a volume column, a note command, a
        stereo or sixteen-bit waveform, a per-sample panning, a sustain loop, a loop that plays
        backwards, or an effect command past the four bits a cell holds — is not a quantity to bound
        and raises where it is met.

        Raises:
            LimitError: when the song carries values this format refuses at its compliance level.
            ValueError: when the song carries content this format has no encoding for.
        """
        require(self.violations())
        return write_module(self.song, self.settings)

    def save(self, path: Path) -> None:
        """Serialise the module and write it to ``path``."""
        path.write_bytes(self.to_bytes())

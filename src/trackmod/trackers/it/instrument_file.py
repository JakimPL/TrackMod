from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import require
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.module.size import SizeReport
from trackmod.schema.config import FROZEN
from trackmod.trackers.it.checks import instrument_violations
from trackmod.trackers.it.instruments.parser import parse_instrument_file
from trackmod.trackers.it.instruments.writer import write_instrument_file
from trackmod.trackers.it.limits import it_limits
from trackmod.trackers.it.sizing import instrument_file_bytes
from trackmod.trackers.it.spec.identity import INSTRUMENT_EXTENSION


class ITInstrumentFile(BaseModel):
    """A standalone Impulse Tracker instrument: one unit, and how strictly it is held.

    A module carries a piece of music; this carries one voice out of it, which is what a producer of
    sampled instruments ships when the instrument rather than the piece is the product. The file states
    the instrument header, the samples its keymap reaches and their waveforms, so a tracker opening it
    gains the voice and leaves its own song alone.
    """

    model_config = FROZEN

    unit: InstrumentUnit
    compliance: Compliance

    @classmethod
    def from_unit(cls, unit: InstrumentUnit, *, compliance: Compliance) -> ITInstrumentFile:
        """Bind a unit to this format at one compliance level."""
        return cls(unit=unit, compliance=compliance)

    @classmethod
    def parse(
        cls,
        data: bytes,
        *,
        compliance: Compliance = Compliance.EXTENDED,
    ) -> ITInstrumentFile:
        """Rebuild a unit from the bytes of an Impulse Tracker instrument file.

        Raises:
            ValueError: when the data does not open with this format's instrument tag.
        """
        return cls(unit=parse_instrument_file(data), compliance=compliance)

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        compliance: Compliance = Compliance.EXTENDED,
    ) -> ITInstrumentFile:
        """Read a unit from an Impulse Tracker instrument file."""
        return cls.parse(path.read_bytes(), compliance=compliance)

    @property
    def extension(self) -> str:
        """The file extension this format writes a standalone instrument with."""
        return INSTRUMENT_EXTENSION

    @property
    def limits(self) -> Limits:
        """The bounds this file is held to, at its compliance level."""
        return it_limits(self.compliance)

    def violations(self) -> tuple[Violation, ...]:
        """Every bound the unit breaks, empty when the file is writable."""
        return instrument_violations(self.unit, limits=self.limits)

    def size(self) -> SizeReport:
        """How many bytes the file occupies, without serialising it."""
        return instrument_file_bytes(self.unit)

    def to_bytes(self) -> bytes:
        """Serialise the whole file.

        Raises:
            LimitError: when the unit carries values this format refuses at its compliance level.
        """
        require(self.violations())
        return write_instrument_file(self.unit)

    def save(self, path: Path) -> None:
        """Serialise the file and write it to ``path``."""
        path.write_bytes(self.to_bytes())

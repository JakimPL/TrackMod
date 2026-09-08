from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import require
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation
from trackmod.module.reaching import Reaching
from trackmod.module.size import SizeReport
from trackmod.schema.config import FROZEN
from trackmod.trackers.it.checks import instrument_violations
from trackmod.trackers.it.instruments.parser import parse_instrument_file
from trackmod.trackers.it.instruments.writer import write_instrument_file
from trackmod.trackers.it.limits import it_limits
from trackmod.trackers.it.sizing import instrument_file_bytes
from trackmod.trackers.it.spec.identity import INSTRUMENT_EXTENSION


class ITInstrumentFile(BaseModel, Reaching):
    """A standalone Impulse Tracker instrument, written as an ``.iti`` file.

    A module carries a piece of music; this carries one voice out of it, which is what a producer of
    sampled instruments ships when the instrument rather than the piece is the product. The file states
    the instrument header, the samples its keymap reaches and their waveforms, so a tracker opening it
    gains the voice and leaves its own song alone.

    Args:
        unit: The instrument and the waveforms its keys reach.
        compliance: How strictly it is held. See :class:`~trackmod.limits.compliance.Compliance`.
    """

    model_config = FROZEN

    unit: InstrumentUnit
    compliance: Compliance

    @classmethod
    def from_unit(cls, unit: InstrumentUnit, *, compliance: Compliance) -> ITInstrumentFile:
        """Bind one instrument and its samples to this format, so it can be sized, checked and written.

        Args:
            unit: The instrument and the waveforms its keys reach. Build one with
                :func:`~trackmod.core.instruments.transfer.extract` or
                :func:`~trackmod.core.instruments.transfer.units`.
            compliance: How strictly to hold it. See
                :class:`~trackmod.limits.compliance.Compliance`.

        Returns:
            The instrument file, ready for :meth:`size`, :meth:`violations` and :meth:`save`.
        """
        return cls(unit=unit, compliance=compliance)

    @classmethod
    def parse(
        cls,
        data: bytes,
        *,
        compliance: Compliance = Compliance.STRUCTURAL,
    ) -> ITInstrumentFile:
        """Read one instrument from the bytes of an Impulse Tracker ``.iti`` file.

        Args:
            data: The whole file.
            compliance: How strictly to grade the values in it. Reading defaults to
                ``Compliance.STRUCTURAL``, because a file that exists is evidence its values fit.

        Returns:
            The instrument file, with the instrument and its samples at ``unit``.

        Raises:
        ValueError: when the data does not open with this format's instrument tag, stops inside
            the header, or holds a keymap naming a sample the file leaves out.

        Warns:
            RepairWarning: when the file holds a value the model has no room for, and it is drawn back
                into range.
            UnnamedByteWarning: when the file holds a byte this format leaves unnamed.
        """
        return cls(unit=parse_instrument_file(data), compliance=compliance)

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        compliance: Compliance = Compliance.STRUCTURAL,
    ) -> ITInstrumentFile:
        """Open an Impulse Tracker ``.iti`` file and read the instrument inside it.

        Args:
            path: The file to read.
            compliance: How strictly to grade the values in it. Reading defaults to
                ``Compliance.STRUCTURAL``, because a file that exists is evidence its values fit.

        Returns:
            The instrument file, with the instrument and its samples at ``unit``.

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
        """The file extension this format writes a standalone instrument with, including the leading dot."""
        return INSTRUMENT_EXTENSION

    @property
    def limits(self) -> Limits:
        """The bounds this file is held to, at its compliance level.

        Returns:
            The limits for this format read at ``compliance``. They are the format's own, so an
            instrument can carry the same values here as inside a module.
        """
        return it_limits(self.compliance)

    def violations(self) -> tuple[Violation, ...]:
        """Every bound the unit breaks at this file's compliance level.

        Returns:
            One :class:`~trackmod.limits.violation.Violation` per value out of range, empty when the
            file is writable. This grades quantities only. Content this format has no encoding for
            reaches you at :meth:`to_bytes` instead.
        """
        return instrument_violations(self.unit, limits=self.limits)

    def exceeded(self) -> tuple[Violation, ...]:
        """Every bound the unit passes at the strictest level, whatever level it is held to.

        A file read back is held to the widest level, because a file that exists is evidence its
        values were storable, so :meth:`violations` stays empty for one a later tracker wrote. This
        answers the other question: which ceilings does it pass, and whose reading does passing them
        cost?

        Returns:
            One :class:`~trackmod.limits.violation.Violation` per ceiling passed, each naming that
            ceiling through the level it broke.
        """
        return instrument_violations(self.unit, limits=it_limits(Compliance.CANONICAL))

    def size(self) -> SizeReport:
        """How many bytes the file occupies, counted from the tables rather than written.

        Returns:
            A size report. ``total`` is the file length, and a file holding one instrument spends
            every byte on records and waveforms.
        """
        return instrument_file_bytes(self.unit)

    def to_bytes(self) -> bytes:
        """Write the whole file as bytes.

        Raises:
            LimitError: when the unit carries values this format refuses at its compliance level.
        Returns:
            The whole file, ready to write to disk or hand on.
        """
        require(self.violations())
        return write_instrument_file(self.unit)

    def save(self, path: Path) -> None:
        """Write the whole file to disk.

        Args:
            path: Where to write it. An existing file is overwritten.

        Raises:
            LimitError: when the unit carries values this format refuses at its compliance level.
            OSError: when the file cannot be written.
        """
        path.write_bytes(self.to_bytes())

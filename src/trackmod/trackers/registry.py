from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final

from trackmod.core.voices.voices import InstrumentVoices, Voices
from trackmod.limits.compliance import Compliance
from trackmod.module.protocol import TrackerModule
from trackmod.module.provenance import Provenance
from trackmod.trackers.it.detection import instrument_written_here as it_instrument_written_here
from trackmod.trackers.it.detection import written_here as it_written_here
from trackmod.trackers.it.instrument_file import ITInstrumentFile
from trackmod.trackers.it.module import ITModule
from trackmod.trackers.it.spec.identity import EXTENSION as IT_EXTENSION
from trackmod.trackers.it.spec.identity import INSTRUMENT_EXTENSION as ITI_EXTENSION
from trackmod.trackers.mod.detection import written_here as mod_written_here
from trackmod.trackers.mod.module import MODModule
from trackmod.trackers.mod.spec.identity import EXTENSION as MOD_EXTENSION
from trackmod.trackers.s3m.detection import written_here as s3m_written_here
from trackmod.trackers.s3m.module import S3MModule
from trackmod.trackers.s3m.spec.identity import EXTENSION as S3M_EXTENSION
from trackmod.trackers.st.detection import written_here as st_written_here
from trackmod.trackers.st.module import STModule
from trackmod.trackers.xm.detection import instrument_written_here as xm_instrument_written_here
from trackmod.trackers.xm.detection import written_here as xm_written_here
from trackmod.trackers.xm.instrument_file import XMInstrumentFile
from trackmod.trackers.xm.module import XMModule
from trackmod.trackers.xm.spec.identity import EXTENSION as XM_EXTENSION
from trackmod.trackers.xm.spec.identity import INSTRUMENT_EXTENSION as XI_EXTENSION

READING_COMPLIANCE: Final = Compliance.STRUCTURAL


def _impulse_tracker_module(data: bytes, compliance: Compliance) -> TrackerModule:
    return ITModule.parse(data, compliance=compliance)


def _fast_tracker_module(data: bytes, compliance: Compliance) -> TrackerModule:
    return XMModule.parse(data, compliance=compliance)


def _scream_tracker_module(data: bytes, compliance: Compliance) -> TrackerModule:
    return S3MModule.parse(data, compliance=compliance)


def _older_amiga(data: bytes) -> bool:
    """Whether the bytes hold the Amiga layout written before any tag existed.

    Both layouts are named with the same extension, because the older one was written before a name
    carried an extension at all. Which one a file holds is therefore read from the bytes, and the tag
    decides it: a file carrying one states which tracker wrote it and is read as that, and the
    fifteen-sample layout is the one whose own records add up to the length of the file instead.
    """
    return st_written_here(data) and not mod_written_here(data)


def _amiga_module(data: bytes, compliance: Compliance) -> TrackerModule:
    """The Amiga module the bytes hold, under whichever of the two layouts written on that machine holds it."""
    binding = STModule if _older_amiga(data) else MODModule
    return binding.parse(data, compliance=compliance)


def _impulse_tracker_instrument(data: bytes) -> Voices:
    unit = ITInstrumentFile.parse(data).unit
    return InstrumentVoices(instruments=(unit.instrument,), samples=unit.samples)


def _fast_tracker_instrument(data: bytes) -> Voices:
    unit = XMInstrumentFile.parse(data).unit
    return InstrumentVoices(instruments=(unit.instrument,), samples=unit.samples)


MODULES: Final[Mapping[str, Callable[[bytes, Compliance], TrackerModule]]] = {
    IT_EXTENSION: _impulse_tracker_module,
    XM_EXTENSION: _fast_tracker_module,
    MOD_EXTENSION: _amiga_module,
    S3M_EXTENSION: _scream_tracker_module,
}

INSTRUMENTS: Final[Mapping[str, Callable[[bytes], Voices]]] = {
    ITI_EXTENSION: _impulse_tracker_instrument,
    XI_EXTENSION: _fast_tracker_instrument,
}

SIGNALS: Final[tuple[tuple[str, Callable[[bytes], bool]], ...]] = (
    (ITI_EXTENSION, it_instrument_written_here),
    (XI_EXTENSION, xm_instrument_written_here),
    (IT_EXTENSION, it_written_here),
    (XM_EXTENSION, xm_written_here),
    (S3M_EXTENSION, s3m_written_here),
    (MOD_EXTENSION, mod_written_here),
    (MOD_EXTENSION, st_written_here),
)

MODULE_EXTENSIONS: Final = frozenset(MODULES)
INSTRUMENT_EXTENSIONS: Final = frozenset(INSTRUMENTS)
EXTENSIONS: Final = MODULE_EXTENSIONS | INSTRUMENT_EXTENSIONS


def reads(extension: str) -> bool:
    """Whether some format here writes files with that extension."""
    return extension.lower() in EXTENSIONS


def parse_module(
    data: bytes,
    *,
    extension: str,
    compliance: Compliance = READING_COMPLIANCE,
) -> TrackerModule:
    """Read a module from bytes, as the format you name.

    Use this when you already hold the bytes, or when you want a file read as a format of your choosing.
    To let the bytes decide instead, pass :func:`detected` as the extension, or open the file with
    :func:`load_module`.

    Args:
        data: The whole file.
        extension: Which format wrote it, with the leading dot, in either upper or lower case. One of
            :data:`MODULE_EXTENSIONS`. Both Amiga layouts use ``.mod`` and are told apart from the bytes.
        compliance: How strictly to grade the values in the file. Reading defaults to
            ``Compliance.STRUCTURAL``, because a file that exists is evidence its values fit.

    Returns:
        The module, as a :class:`~trackmod.module.protocol.TrackerModule`. Every format answers that
        protocol, so a loop over a mixed folder reaches each file's song, provenance and size report
        the same way.

    Raises:
        ValueError: when no module format writes that extension, or the bytes belong to another one.

    Warns:
        RepairWarning: when the file holds a value the model has no room for, and it is drawn back into
            range.
        UnnamedByteWarning: when the file holds a byte this library has no name for.
    """
    reader = MODULES.get(extension.lower())
    if reader is None:
        understood = ", ".join(sorted(MODULES))
        raise ValueError(f"{extension!r} names no module format here; {understood} are the ones written")

    return reader(data, compliance)


def load_module(path: Path, *, compliance: Compliance = READING_COMPLIANCE) -> TrackerModule:
    """Open a module file and read the song inside it.

    The format comes from the file contents rather than its name, so a file that was renamed or saved
    under the wrong extension still opens. To read bytes you already hold, or to name the format
    yourself, use :func:`parse_module`.

    Args:
        path: The file to read.
        compliance: How strictly to grade the values in the file. Reading defaults to
            ``Compliance.STRUCTURAL``, because a file that exists is evidence its values fit.

    Returns:
        The module, as a :class:`~trackmod.module.protocol.TrackerModule`. The music is at
        ``module.song``, the program that wrote the file at ``module.provenance``, and the byte counts
        at ``module.size()``.

    Raises:
        OSError: when the file cannot be read.
        ValueError: when the bytes match none of the five module formats, or match a single instrument
            file. Read ``.iti`` and ``.xi`` with :func:`load_voices`.

    Warns:
        RepairWarning: when the file holds a value the model has no room for, and it is drawn back into
            range.
        UnnamedByteWarning: when the file holds a byte this library has no name for.
    """
    data = path.read_bytes()
    return parse_module(data, extension=detected(data), compliance=compliance)


def parse_voices(data: bytes, *, extension: str) -> Voices:
    """Read a voice table from bytes, as the format you name.

    A module holds as many voices as it was written with, and a single instrument file holds one, so
    this reads either the same way.

    Args:
        data: The whole file.
        extension: Which format wrote it, with the leading dot, in either upper or lower case. One of
            :data:`EXTENSIONS`.

    Returns:
        :class:`~trackmod.core.voices.voices.SampleVoices` when that format's cells name samples, and
        :class:`~trackmod.core.voices.voices.InstrumentVoices` when they name instruments. Both answer
        ``samples`` and ``slots``, so the waveforms are one attribute away either way.

    Raises:
        ValueError: when no format writes that extension, or the bytes belong to another one.

    Warns:
        RepairWarning: when the file holds a value the model has no room for, and it is drawn back into
            range.
        UnnamedByteWarning: when the file holds a byte this library has no name for.
    """
    named = extension.lower()
    if named in MODULES:
        return parse_module(data, extension=named).song.voices

    reader = INSTRUMENTS.get(named)
    if reader is None:
        understood = ", ".join(sorted(EXTENSIONS))
        raise ValueError(f"{extension!r} names no format here; {understood} are the ones written")

    return reader(data)


def load_voices(path: Path) -> Voices:
    """Open a module or single instrument file and read the voices inside it.

    The format comes from the file contents rather than its name, and both kinds of container are read
    the same way, so one loop over a folder reaches the sounds of every file in it.

    Args:
        path: The file to read.

    Returns:
        :class:`~trackmod.core.voices.voices.SampleVoices` when that format's cells name samples, and
        :class:`~trackmod.core.voices.voices.InstrumentVoices` when they name instruments.

    Raises:
        OSError: when the file cannot be read.
        ValueError: when the bytes match none of the formats read here.

    Warns:
        RepairWarning: when the file holds a value the model has no room for, and it is drawn back into
            range.
        UnnamedByteWarning: when the file holds a byte this library has no name for.
    """
    data = path.read_bytes()
    return parse_voices(data, extension=detected(data))


def parse_provenance(data: bytes, *, extension: str) -> Provenance | None:
    """What the bytes state about the program that wrote them, or ``None`` for a format stating none.

    Which format wrote them is what the extension states, in either capitalization, and the two sharing
    ``.mod`` are told apart from the bytes as :func:`parse_voices` tells them apart. The tag is what the
    newer of those two states and the whole of what it has, and the older one states nothing at all, so
    which layout the bytes hold is what settles whether there is an answer.

    Raises:
        ValueError: when no module format writes that extension, or the data reads as another one.
    """
    return parse_module(data, extension=extension).provenance


def detected(data: bytes) -> str:
    """Work out which format wrote the bytes, whatever the file was named.

    Four of the five formats open with a tag or a name of their own. The fifth has neither, and is
    recognized because its records add up to the length of the file. Tags are checked first, so a tag
    settles the answer before the arithmetic is tried.

    Args:
        data: The whole file. Only the opening bytes and the total length decide the answer.

    Returns:
        The extension, with the leading dot: one of :data:`EXTENSIONS`. Both Amiga layouts answer
        ``.mod``, and :func:`parse_module` tells those two apart when it reads them.

    Raises:
        ValueError: when the bytes match none of the formats read here.

    Example:
        >>> from trackmod import detected
        >>> detected(b"IMPM" + bytes(60))
        '.it'
    """
    for extension, states in SIGNALS:
        if states(data):
            return extension

    raise ValueError(f"the {len(data)} bytes state none of the formats written here")

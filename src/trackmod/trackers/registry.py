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
    """The module the bytes hold, bound to the format that wrote them.

    What comes back answers :class:`~trackmod.module.protocol.TrackerModule`, so a caller reading a whole
    collection holds every format the same way and reaches the song, the provenance and the size report
    of each through one surface. Which format wrote them is what the extension states, in either
    capitalisation, and the two sharing ``.mod`` are told apart from the bytes.

    Raises:
        ValueError: when no module format writes that extension, or the data reads as another one.
    """
    reader = MODULES.get(extension.lower())
    if reader is None:
        understood = ", ".join(sorted(MODULES))
        raise ValueError(f"{extension!r} names no module format here; {understood} are the ones written")

    return reader(data, compliance)


def load_module(path: Path, *, compliance: Compliance = READING_COMPLIANCE) -> TrackerModule:
    """The module a file holds, read as the format its own bytes state.

    The name the file arrived under is one a collection may have lost or changed, so the format comes
    from :func:`detected` and the file opens as what it is. Pass the bytes to :func:`parse_module` with
    an extension of your own to read one as a format you name instead.

    Raises:
        ValueError: when the bytes state none of the module formats written here.
    """
    data = path.read_bytes()
    return parse_module(data, extension=detected(data), compliance=compliance)


def parse_voices(data: bytes, *, extension: str) -> Voices:
    """The voice table the bytes hold, in the shape the format that wrote them addresses it.

    A module carries as many voices as it was written with and a standalone instrument file carries one,
    so both answer the same question and a caller holding bytes reads either the same way. What comes
    back says which kind of table it is: a song whose cells name samples reads back as
    :class:`~trackmod.core.voices.voices.SampleVoices`, and one whose cells name instruments as
    :class:`~trackmod.core.voices.voices.InstrumentVoices`. Which format wrote them is what the
    extension states, in either capitalisation.

    Raises:
        ValueError: when no format writes that extension, or the data reads as another one.
    """
    named = extension.lower()
    if named in MODULES:
        return parse_module(data, extension=named).song.voices

    reader = INSTRUMENTS.get(named)
    if reader is None:
        understood = ", ".join(sorted(EXTENSIONS))
        raise ValueError(f"{extension!r} names no format here; {understood} are the ones written")

    return reader(data)


def parse_provenance(data: bytes, *, extension: str) -> Provenance | None:
    """What the bytes state about the program that wrote them, or ``None`` for a format stating none.

    Which format wrote them is what the extension states, in either capitalisation, and the two sharing
    ``.mod`` are told apart from the bytes as :func:`parse_voices` tells them apart. The tag is what the
    newer of those two states and the whole of what it has, and the older one states nothing at all, so
    which layout the bytes hold is what settles whether there is an answer.

    Raises:
        ValueError: when no module format writes that extension, or the data reads as another one.
    """
    return parse_module(data, extension=extension).provenance


def detected(data: bytes) -> str:
    """The extension the bytes themselves state, whatever name they arrived under.

    Every format but one opens a file with a tag or a name of its own, and the one that opens with
    neither is recognised by its records adding up to the length of the file. The strongest statement
    wins, so a tag a reader knows settles the answer before the arithmetic is asked.

    The two formats sharing ``.mod`` both answer with that suffix, and which of them holds the bytes
    stays where it already was, with :func:`parse_module`. Pass the answer there to read bytes whose
    name is unknown or wrong, or reach for :func:`load_module`, which asks this of a file for you.

    Raises:
        ValueError: when the bytes state none of the formats written here.
    """
    for extension, states in SIGNALS:
        if states(data):
            return extension

    raise ValueError(f"the {len(data)} bytes state none of the formats written here")

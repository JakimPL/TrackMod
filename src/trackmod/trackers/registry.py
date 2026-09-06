from collections.abc import Callable, Mapping
from typing import Final

from trackmod.core.voices.voices import InstrumentVoices, Voices
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


def _impulse_tracker_module(data: bytes) -> Voices:
    return ITModule.parse(data).song.voices


def _fast_tracker_module(data: bytes) -> Voices:
    return XMModule.parse(data).song.voices


def _older_amiga(data: bytes) -> bool:
    """Whether the bytes hold the Amiga layout written before any tag existed.

    Both layouts are named with the same extension, because the older one was written before a name
    carried an extension at all. Which one a file holds is therefore read from the bytes, and the tag
    decides it: a file carrying one states which tracker wrote it and is read as that, and the
    fifteen-sample layout is the one whose own records add up to the length of the file instead.
    """
    return st_written_here(data) and not mod_written_here(data)


def _amiga_module(data: bytes) -> Voices:
    """The voices of an Amiga module, whichever of the two layouts written on that machine holds them."""
    binding = STModule if _older_amiga(data) else MODModule
    return binding.parse(data).song.voices


def _scream_tracker_module(data: bytes) -> Voices:
    return S3MModule.parse(data).song.voices


def _impulse_tracker_instrument(data: bytes) -> Voices:
    unit = ITInstrumentFile.parse(data).unit
    return InstrumentVoices(instruments=(unit.instrument,), samples=unit.samples)


def _fast_tracker_instrument(data: bytes) -> Voices:
    unit = XMInstrumentFile.parse(data).unit
    return InstrumentVoices(instruments=(unit.instrument,), samples=unit.samples)


def _impulse_tracker_writer(data: bytes) -> Provenance | None:
    return ITModule.parse(data).provenance


def _fast_tracker_writer(data: bytes) -> Provenance | None:
    return XMModule.parse(data).provenance


def _scream_tracker_writer(data: bytes) -> Provenance | None:
    return S3MModule.parse(data).provenance


def _amiga_writer(data: bytes) -> Provenance | None:
    """What an Amiga module states about the program that wrote it, under whichever layout holds it.

    The tag is what the newer layout states and the whole of what it has, and the older one states
    nothing at all, so which layout the bytes hold is what settles whether there is an answer.
    """
    return None if _older_amiga(data) else MODModule.parse(data).provenance


READERS: Final[Mapping[str, Callable[[bytes], Voices]]] = {
    IT_EXTENSION: _impulse_tracker_module,
    XM_EXTENSION: _fast_tracker_module,
    MOD_EXTENSION: _amiga_module,
    S3M_EXTENSION: _scream_tracker_module,
    ITI_EXTENSION: _impulse_tracker_instrument,
    XI_EXTENSION: _fast_tracker_instrument,
}

WRITER_READERS: Final[Mapping[str, Callable[[bytes], Provenance | None]]] = {
    IT_EXTENSION: _impulse_tracker_writer,
    XM_EXTENSION: _fast_tracker_writer,
    MOD_EXTENSION: _amiga_writer,
    S3M_EXTENSION: _scream_tracker_writer,
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

MODULE_EXTENSIONS: Final = frozenset({IT_EXTENSION, XM_EXTENSION, MOD_EXTENSION, S3M_EXTENSION})
INSTRUMENT_EXTENSIONS: Final = frozenset({ITI_EXTENSION, XI_EXTENSION})
EXTENSIONS: Final = MODULE_EXTENSIONS | INSTRUMENT_EXTENSIONS


def reads(extension: str) -> bool:
    """Whether some format here writes files with that extension."""
    return extension.lower() in READERS


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
    reader = READERS.get(extension.lower())
    if reader is None:
        understood = ", ".join(sorted(READERS))
        raise ValueError(f"{extension!r} names no format here; {understood} are the ones written")

    return reader(data)


def parse_provenance(data: bytes, *, extension: str) -> Provenance | None:
    """What the bytes state about the program that wrote them, or ``None`` for a format stating none.

    Which format wrote them is what the extension states, in either capitalisation, and the two sharing
    ``.mod`` are told apart from the bytes as :func:`parse_voices` tells them apart.

    Raises:
        ValueError: when no module format writes that extension, or the data reads as another one.
    """
    reader = WRITER_READERS.get(extension.lower())
    if reader is None:
        understood = ", ".join(sorted(WRITER_READERS))
        raise ValueError(f"{extension!r} names no module format here; {understood} are the ones written")

    return reader(data)


def detected(data: bytes) -> str:
    """The extension the bytes themselves state, whatever name they arrived under.

    Every format but one opens a file with a tag or a name of its own, and the one that opens with
    neither is recognised by its records adding up to the length of the file. The strongest statement
    wins, so a tag a reader knows settles the answer before the arithmetic is asked.

    The two formats sharing ``.mod`` both answer with that suffix, and which of them holds the bytes
    stays where it already was, with :func:`parse_voices`. Pass the answer there to read bytes whose
    name is unknown or wrong.

    Raises:
        ValueError: when the bytes state none of the formats written here.
    """
    for extension, states in SIGNALS:
        if states(data):
            return extension

    raise ValueError(f"the {len(data)} bytes state none of the formats written here")

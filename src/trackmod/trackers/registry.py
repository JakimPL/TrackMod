from collections.abc import Callable, Mapping
from typing import Final

from trackmod.core.voices.voices import InstrumentVoices, Voices
from trackmod.trackers.it.instrument_file import ITInstrumentFile
from trackmod.trackers.it.module import ITModule
from trackmod.trackers.it.spec.identity import EXTENSION as IT_EXTENSION
from trackmod.trackers.it.spec.identity import INSTRUMENT_EXTENSION as ITI_EXTENSION
from trackmod.trackers.xm.instrument_file import XMInstrumentFile
from trackmod.trackers.xm.module import XMModule
from trackmod.trackers.xm.spec.identity import EXTENSION as XM_EXTENSION
from trackmod.trackers.xm.spec.identity import INSTRUMENT_EXTENSION as XI_EXTENSION


def _impulse_tracker_module(data: bytes) -> Voices:
    return ITModule.parse(data).song.voices


def _fast_tracker_module(data: bytes) -> Voices:
    return XMModule.parse(data).song.voices


def _impulse_tracker_instrument(data: bytes) -> Voices:
    unit = ITInstrumentFile.parse(data).unit
    return InstrumentVoices(instruments=(unit.instrument,), samples=unit.samples)


def _fast_tracker_instrument(data: bytes) -> Voices:
    unit = XMInstrumentFile.parse(data).unit
    return InstrumentVoices(instruments=(unit.instrument,), samples=unit.samples)


READERS: Final[Mapping[str, Callable[[bytes], Voices]]] = {
    IT_EXTENSION: _impulse_tracker_module,
    XM_EXTENSION: _fast_tracker_module,
    ITI_EXTENSION: _impulse_tracker_instrument,
    XI_EXTENSION: _fast_tracker_instrument,
}

MODULE_EXTENSIONS: Final = frozenset({IT_EXTENSION, XM_EXTENSION})
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

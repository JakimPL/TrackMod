from typing import Final

from trackmod.binary.cursor import Cursor
from trackmod.binary.records.values import RecordValues, read_bytes, read_int
from trackmod.binary.text import decode_name
from trackmod.core.envelopes.kind import EnvelopeKind
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.keymap import Keymap
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.spec.pitch import NOTE_COUNT
from trackmod.trackers.xm.instruments.envelope import parse_envelope
from trackmod.trackers.xm.instruments.keymap import parse_keymap
from trackmod.trackers.xm.layout.instrument import INSTRUMENT_FILE_HEADER
from trackmod.trackers.xm.samples.parser import read_samples
from trackmod.trackers.xm.spec.identity import MAGIC_INSTRUMENT

SILENT_KEYMAP: Keymap = (None,) * NOTE_COUNT
FIRST_SAMPLE: Final = 0


def instrument_keymap(values: RecordValues, *, offset: int, length: int) -> Keymap:
    """The keyboard routing a stored instrument carries, silent when it owns nothing to route to."""
    if length == 0:
        return SILENT_KEYMAP

    return parse_keymap(read_bytes(values, "keymap"), offset=offset, length=length)


def parse_instrument(values: RecordValues, *, offset: int, length: int) -> Instrument:
    """Rebuild an instrument from its unpacked header fields and where its samples land in the module."""
    return Instrument(
        name=decode_name(read_bytes(values, "name")),
        keymap=instrument_keymap(values, offset=offset, length=length),
        volume_envelope=parse_envelope(EnvelopeKind.VOLUME, values),
        panning_envelope=parse_envelope(EnvelopeKind.PANNING, values),
        fadeout=read_int(values, "fadeout"),
    )


def parse_stub(values: RecordValues) -> Instrument:
    """Rebuild an instrument written in the short form, which owns nothing and so shapes nothing."""
    return Instrument(
        name=decode_name(read_bytes(values, "name")),
        keymap=SILENT_KEYMAP,
    )


def parse_instrument_file(data: bytes) -> InstrumentUnit:
    """Rebuild a unit from the bytes of a standalone FastTracker 2 instrument file.

    The file is walked front to back the way a module is: the header states how many samples follow, and
    every one of their headers precedes every one of their waveforms.

    Raises:
        ValueError: when the data does not open with this format's instrument tag.
    """
    cursor = Cursor(data)
    values = cursor.read(INSTRUMENT_FILE_HEADER)
    if read_bytes(values, "magic") != MAGIC_INSTRUMENT:
        raise ValueError("data does not open with the FastTracker 2 instrument tag")

    count = read_int(values, "sample_count")
    return InstrumentUnit(
        instrument=parse_instrument(values, offset=FIRST_SAMPLE, length=count),
        samples=read_samples(cursor, count=count),
    )

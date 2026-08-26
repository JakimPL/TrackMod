from trackmod.binary.records.values import RecordValues, read_bytes, read_int, read_rows
from trackmod.binary.text import decode_name
from trackmod.core.envelopes.kind import EnvelopeKind
from trackmod.core.instruments.behaviour import (
    DuplicateAction,
    DuplicateCheck,
    NewNoteAction,
)
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.trackers.it.instruments.envelope import parse_envelope
from trackmod.trackers.it.instruments.keymap import parse_keymap
from trackmod.trackers.it.layout.instrument import INSTRUMENT_HEADER
from trackmod.trackers.it.panning import shared_panning
from trackmod.trackers.it.samples.parser import read_sample
from trackmod.trackers.it.spec.flags import SamplePanning
from trackmod.trackers.it.spec.identity import DOUBLED_COMPRESSION, MAGIC_INSTRUMENT
from trackmod.trackers.it.spec.sizes import INSTRUMENT_HEADER_BYTES, SAMPLE_HEADER_BYTES


def parse_instrument(values: RecordValues) -> Instrument:
    """Rebuild an instrument from its unpacked header fields."""
    panning = read_int(values, "default_pan")
    return Instrument(
        name=decode_name(read_bytes(values, "name")),
        keymap=parse_keymap(read_rows(values, "note_map")),
        volume_envelope=parse_envelope(EnvelopeKind.VOLUME, values),
        panning_envelope=parse_envelope(EnvelopeKind.PANNING, values),
        pitch_envelope=parse_envelope(EnvelopeKind.PITCH, values),
        fadeout=read_int(values, "fadeout"),
        global_volume=read_int(values, "global_volume"),
        panning=None if panning & SamplePanning.ENABLED else shared_panning(panning),
        new_note_action=NewNoteAction(read_int(values, "new_note_action")),
        duplicate_check=DuplicateCheck(read_int(values, "duplicate_check")),
        duplicate_action=DuplicateAction(read_int(values, "duplicate_action")),
    )


def parse_instrument_file(data: bytes) -> InstrumentUnit:
    """Rebuild a unit from the bytes of a standalone Impulse Tracker instrument file.

    The header states how many samples follow it, and their headers sit end to end behind it, so the
    position of each one is arithmetic on two record sizes.

    Raises:
        ValueError: when the data opens with something other than this format's instrument tag, or the
            keymap names a sample the file leaves out.
    """
    values = INSTRUMENT_HEADER.unpack(data)
    if read_bytes(values, "magic") != MAGIC_INSTRUMENT:
        raise ValueError("data does not open with the Impulse Tracker instrument tag")

    count = read_int(values, "sample_count")
    doubled = read_int(values, "tracker_version") >= DOUBLED_COMPRESSION
    samples = tuple(
        read_sample(data, offset=INSTRUMENT_HEADER_BYTES + SAMPLE_HEADER_BYTES * index, doubled=doubled)
        for index in range(count)
    )
    return InstrumentUnit(instrument=parse_instrument(values), samples=samples)

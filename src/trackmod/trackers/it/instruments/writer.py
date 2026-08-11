from trackmod.binary.layout import offsets
from trackmod.binary.records.values import ArrayValue, FieldValue
from trackmod.binary.text import encode_name
from trackmod.core.envelopes.kind import EnvelopeKind
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.trackers.it.instruments.envelope import envelope_values
from trackmod.trackers.it.instruments.keymap import note_map
from trackmod.trackers.it.layout.instrument import INSTRUMENT_HEADER
from trackmod.trackers.it.panning import stored_panning
from trackmod.trackers.it.samples.writer import sample_bytes, sample_header
from trackmod.trackers.it.spec.defaults import C5_NOTE, PANNING_DISABLED
from trackmod.trackers.it.spec.identity import CREATED_WITH, MAGIC_INSTRUMENT
from trackmod.trackers.it.spec.sizes import (
    FILENAME_BYTES,
    INSTRUMENT_HEADER_BYTES,
    NAME_BYTES,
    SAMPLE_HEADER_BYTES,
)


def instrument_header(instrument: Instrument, *, samples: int) -> bytes:
    """Serialise an instrument header, its keyboard routing and its three envelopes.

    ``samples`` is how many sample slots the container behind this header holds for the instrument,
    which a module reads off its own table and a standalone file reads off this count alone.

    The header states the version it was written to (:data:`~trackmod.trackers.it.spec.identity
    .CREATED_WITH`), which is what a standalone instrument file is read by: a module hands its loader the
    version its own file header carries, while an instrument travelling on its own carries the only copy
    of it, and the versions from 2.00 onward are the ones laying the envelopes out where this writer puts
    them.
    """
    panning = PANNING_DISABLED if instrument.panning is None else stored_panning(instrument.panning)
    values: dict[str, FieldValue | ArrayValue] = {
        "magic": MAGIC_INSTRUMENT,
        "filename": encode_name(instrument.name, FILENAME_BYTES),
        "new_note_action": int(instrument.new_note_action),
        "duplicate_check": int(instrument.duplicate_check),
        "duplicate_action": int(instrument.duplicate_action),
        "fadeout": instrument.fadeout,
        "pitch_pan_separation": 0,
        "pitch_pan_center": C5_NOTE,
        "global_volume": instrument.global_volume,
        "default_pan": panning,
        "random_volume": 0,
        "random_panning": 0,
        "tracker_version": CREATED_WITH,
        "sample_count": samples,
        "name": encode_name(instrument.name, NAME_BYTES),
        "filter_cutoff": 0,
        "filter_resonance": 0,
        "midi_channel": 0,
        "midi_program": 0,
        "midi_bank": 0,
        "note_map": note_map(instrument.keymap),
    }
    for kind in EnvelopeKind:
        values.update(envelope_values(kind, instrument.envelope(kind)))

    return INSTRUMENT_HEADER.pack(values)


def write_instrument_file(unit: InstrumentUnit) -> bytes:
    """Serialise one unit as a whole standalone Impulse Tracker instrument file.

    The file is the instrument header, then a header for each sample the unit holds, then the waveforms,
    with each header pointing at frames counted from the start of the file — the same records and the
    same pointers a module writes, laid out for a container holding one instrument.
    """
    frames = [sample_bytes(sample) for sample in unit.samples]
    data_at = INSTRUMENT_HEADER_BYTES + SAMPLE_HEADER_BYTES * len(unit.samples)
    headers = [
        sample_header(sample, data_offset=offset) for sample, offset in zip(unit.samples, offsets(frames, data_at))
    ]
    return b"".join([instrument_header(unit.instrument, samples=len(unit.samples)), *headers, *frames])

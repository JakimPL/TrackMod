from trackmod.binary.records.values import ArrayValue, FieldValue
from trackmod.binary.text import encode_name
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.trackers.xm.instruments.envelope import envelope_values
from trackmod.trackers.xm.instruments.group import SampleGroup
from trackmod.trackers.xm.instruments.grouping import group_samples
from trackmod.trackers.xm.instruments.keymap import stored_keymap
from trackmod.trackers.xm.layout.envelope import ENVELOPE_KINDS
from trackmod.trackers.xm.layout.instrument import (
    EMPTY_INSTRUMENT_HEADER,
    INSTRUMENT_FILE_HEADER,
    INSTRUMENT_HEADER,
)
from trackmod.trackers.xm.samples.writer import sample_bytes, sample_header
from trackmod.trackers.xm.spec.defaults import DEFAULT_TRACKER, INSTRUMENT_TYPE
from trackmod.trackers.xm.spec.identity import (
    INSTRUMENT_VERSION,
    MAGIC_INSTRUMENT,
    STRIPPED_BYTE,
)
from trackmod.trackers.xm.spec.sizes import (
    EMPTY_INSTRUMENT_HEADER_BYTES,
    INSTRUMENT_HEADER_BYTES,
    NAME_BYTES,
    SAMPLE_HEADER_BYTES,
    TRACKER_NAME_BYTES,
)


def identity_values(
    instrument: Instrument,
    group: SampleGroup,
    *,
    size: int,
) -> dict[str, FieldValue]:
    """The four fields both forms of a module's instrument header open with."""
    return {
        "header_size": size,
        "name": encode_name(instrument.name, NAME_BYTES),
        "type": INSTRUMENT_TYPE,
        "sample_count": group.length,
    }


def body_values(instrument: Instrument, group: SampleGroup) -> dict[str, FieldValue | ArrayValue]:
    """The keyboard routing, envelopes and fadeout every instrument header lays out behind its identity.

    Raises:
        ValueError: when the instrument carries a pitch envelope, which this format has no room for.
    """
    if instrument.pitch_envelope is not None:
        raise ValueError(f"instrument {instrument.name!r} carries a pitch envelope, which this format cannot store")

    values: dict[str, FieldValue | ArrayValue] = {
        "keymap": stored_keymap(group.keymap),
        "vibrato_type": 0,
        "vibrato_sweep": 0,
        "vibrato_depth": 0,
        "vibrato_rate": 0,
        "fadeout": instrument.fadeout,
    }
    for kind in ENVELOPE_KINDS:
        values.update(envelope_values(kind, instrument.envelope(kind)))

    return values


def empty_header(instrument: Instrument, group: SampleGroup) -> bytes:
    """The short header a stored instrument that owns nothing is written as."""
    return EMPTY_INSTRUMENT_HEADER.pack(
        identity_values(instrument, group, size=EMPTY_INSTRUMENT_HEADER_BYTES),
    )


def instrument_header(instrument: Instrument, group: SampleGroup) -> bytes:
    """Serialise an instrument header, its keyboard routing and its two envelopes.

    An instrument that owns no samples is written in the short form the format reserves for it, which
    stops after the sample count rather than reserving room for a keymap nothing would route through.

    Raises:
        ValueError: when the instrument carries a pitch envelope, which this format has no room for.
    """
    if group.length == 0:
        return empty_header(instrument, group)

    values: dict[str, FieldValue | ArrayValue] = {
        **identity_values(instrument, group, size=INSTRUMENT_HEADER_BYTES),
        "sample_header_size": SAMPLE_HEADER_BYTES,
        "reserved": 0,
        **body_values(instrument, group),
    }
    return INSTRUMENT_HEADER.pack(values)


def instrument_file_header(instrument: Instrument, group: SampleGroup) -> bytes:
    """Serialise the header a standalone instrument file opens with.

    A file of one instrument names itself and the tracker that wrote it where a module's header states a
    size and a type, and it counts its samples last; behind that, the two lay out the same body.

    Raises:
        ValueError: when the instrument carries a pitch envelope, which this format has no room for.
    """
    values: dict[str, FieldValue | ArrayValue] = {
        "magic": MAGIC_INSTRUMENT,
        "name": encode_name(instrument.name, NAME_BYTES),
        "stripped": STRIPPED_BYTE,
        "tracker": encode_name(DEFAULT_TRACKER, TRACKER_NAME_BYTES),
        "version": INSTRUMENT_VERSION,
        "sample_count": group.length,
        **body_values(instrument, group),
    }
    return INSTRUMENT_FILE_HEADER.pack(values)


def sample_block(group: SampleGroup) -> bytes:
    """One instrument's samples as a file lays them out: every header, then every waveform."""
    headers = b"".join(sample_header(sample, tuning=tuning) for sample, tuning in zip(group.samples, group.tunings))
    return headers + b"".join(sample_bytes(sample) for sample in group.samples)


def instrument_block(instrument: Instrument, group: SampleGroup) -> bytes:
    """One instrument as a module lays it out: its header, then every sample header, then every waveform."""
    return instrument_header(instrument, group) + sample_block(group)


def write_instrument_file(unit: InstrumentUnit) -> bytes:
    """Serialise one unit as a whole standalone FastTracker 2 instrument file.

    The unit's samples are grouped the way a stored instrument owns them, so the file carries the same
    waveforms, transpositions and keymap positions a module writing this instrument would.

    Raises:
        ValueError: when the unit carries content this format has no encoding for.
    """
    group = group_samples(unit.instrument, unit.samples)
    return instrument_file_header(unit.instrument, group) + sample_block(group)


def waveform_bytes(group: SampleGroup) -> int:
    """How many bytes one instrument's waveforms occupy, counting a shared sample once per owner."""
    return sum(sample.stored_bytes for sample in group.samples)

from pathlib import Path

import numpy as np
import pytest

from tests.conftest import keyed, voices_of
from trackmod.binary.records.field import Field
from trackmod.binary.records.record import Record
from trackmod.core.envelopes.envelope import Envelope
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.keymap import routed_keymap
from trackmod.core.instruments.transfer import extract
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.core.notes.pitch import Note
from trackmod.core.songs.song import Song
from trackmod.limits.capability import Capability
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import LimitError
from trackmod.limits.severity import Severity
from trackmod.trackers.xm.instrument_file import XMInstrumentFile
from trackmod.trackers.xm.layout.instrument import INSTRUMENT_FILE_HEADER
from trackmod.trackers.xm.spec.identity import (
    INSTRUMENT_EXTENSION,
    INSTRUMENT_VERSION,
    MAGIC_INSTRUMENT,
    STRIPPED_BYTE,
)
from trackmod.trackers.xm.spec.sizes import (
    INSTRUMENT_FILE_COUNT_OFFSET,
    INSTRUMENT_FILE_HEADER_BYTES,
    SAMPLE_HEADER_BYTES,
)

PIANO = 0
STAGED_GAIN = 24
STRIPPED_OFFSET = 43
VERSION_OFFSET = 64
BODY_OFFSETS = {"keymap": 66, "volume_points": 162, "panning_points": 210, "volume_count": 258, "fadeout": 272}


def instrument_file(unit: InstrumentUnit, *, compliance: Compliance = Compliance.EXTENDED) -> XMInstrumentFile:
    return XMInstrumentFile.from_unit(unit, compliance=compliance)


def piano(xm_song: Song) -> InstrumentUnit:
    """The song's enveloped instrument, which is the unit these tests carry."""
    return extract(voices_of(xm_song), PIANO)


def described(record: Record, name: str) -> int:
    """Where the record lays one field out, whichever kind of field it is."""
    fields: tuple[Field, ...] = record.fields
    for field in (*fields, *record.arrays):
        if field.name == name:
            return field.offset

    raise KeyError(name)


def test_the_file_opens_with_the_instrument_signature(xm_song: Song) -> None:
    assert instrument_file(piano(xm_song)).to_bytes().startswith(MAGIC_INSTRUMENT)


def test_the_header_states_the_two_marks_a_reader_checks(xm_song: Song) -> None:
    data = instrument_file(piano(xm_song)).to_bytes()
    assert data[STRIPPED_OFFSET] == STRIPPED_BYTE
    assert int.from_bytes(data[VERSION_OFFSET : VERSION_OFFSET + 2], "little") == INSTRUMENT_VERSION


def test_the_sample_count_closes_the_header(xm_song: Song) -> None:
    unit = piano(xm_song)
    data = instrument_file(unit).to_bytes()
    counted = int.from_bytes(data[INSTRUMENT_FILE_COUNT_OFFSET : INSTRUMENT_FILE_COUNT_OFFSET + 2], "little")
    assert counted == len(unit.samples)
    assert INSTRUMENT_FILE_HEADER.size == INSTRUMENT_FILE_HEADER_BYTES


def test_the_body_sits_where_this_format_states_a_standalone_header_puts_it() -> None:
    # The identity block is longer than a module's, and the body behind it is the same layout moved on.
    for name, offset in BODY_OFFSETS.items():
        assert described(INSTRUMENT_FILE_HEADER, name) == offset


def test_the_size_model_agrees_with_the_written_file(xm_song: Song) -> None:
    written = instrument_file(piano(xm_song))
    report = written.size()
    assert report.total == len(written.to_bytes())
    assert report.total == report.headers + report.pcm
    assert report.patterns == 0


def test_a_written_instrument_parses_back_to_the_same_voice(xm_song: Song) -> None:
    original = piano(xm_song).instrument
    recovered = XMInstrumentFile.parse(instrument_file(piano(xm_song)).to_bytes()).unit.instrument
    assert recovered.name == original.name
    assert recovered.keymap == original.keymap
    assert recovered.volume_envelope == original.volume_envelope
    assert recovered.fadeout == original.fadeout


def test_the_waveforms_survive_a_round_trip(xm_song: Song) -> None:
    unit = piano(xm_song)
    recovered = XMInstrumentFile.parse(instrument_file(unit).to_bytes()).unit
    for original, restored in zip(unit.samples, recovered.samples):
        assert restored.name == original.name
        assert restored.rate == original.rate
        assert restored.depth == original.depth
        assert restored.loop == original.loop
        assert np.array_equal(restored.pcm, original.pcm)


def test_an_instrument_owning_nothing_is_the_header_alone() -> None:
    reserved = InstrumentUnit(instrument=Instrument(name="", keymap=routed_keymap({})), samples=())
    data = instrument_file(reserved).to_bytes()
    assert len(data) == INSTRUMENT_FILE_HEADER_BYTES
    assert XMInstrumentFile.parse(data).unit.samples == ()


def test_one_more_sample_grows_the_file_by_its_header_and_its_frames(xm_song: Song) -> None:
    one, two = extract(voices_of(xm_song), 1), piano(xm_song)
    growth = len(instrument_file(two).to_bytes()) - len(instrument_file(one).to_bytes())
    assert growth == SAMPLE_HEADER_BYTES * (len(two.samples) - len(one.samples)) + (
        sum(sample.stored_bytes for sample in two.samples) - sum(sample.stored_bytes for sample in one.samples)
    )


def test_a_file_saves_and_loads_under_its_own_extension(tmp_path: Path, xm_song: Song) -> None:
    written = instrument_file(piano(xm_song))
    path = tmp_path / f"piano{written.extension}"
    written.save(path)
    assert written.extension == INSTRUMENT_EXTENSION
    assert XMInstrumentFile.load(path).unit.instrument.name == piano(xm_song).instrument.name


def test_a_sample_staged_below_full_gain_is_reported_at_every_compliance(xm_song: Song) -> None:
    # This format has no per-sample multiplier, so a bank staged with one belongs to a file produced for
    # the format it will be played in.
    unit = piano(xm_song)
    staged = unit.model_copy(
        update={"samples": tuple(sample.model_copy(update={"gain": STAGED_GAIN}) for sample in unit.samples)}
    )
    for compliance in Compliance:
        (reported,) = instrument_file(staged, compliance=compliance).violations()
        assert reported.capability is Capability.SAMPLE_GAIN
        assert reported.severity is Severity.STRUCTURAL

    with pytest.raises(LimitError):
        instrument_file(staged).to_bytes()


def test_a_pitch_envelope_is_refused_where_it_is_met(xm_song: Song, fade_envelope: Envelope) -> None:
    unit = piano(xm_song)
    shaped = unit.model_copy(
        update={"instrument": unit.instrument.model_copy(update={"pitch_envelope": fade_envelope})}
    )
    with pytest.raises(ValueError, match="pitch envelope"):
        instrument_file(shaped).to_bytes()


def test_parsing_something_that_is_not_an_instrument_raises() -> None:
    with pytest.raises(ValueError, match="FastTracker 2 instrument tag"):
        XMInstrumentFile.parse(b"not an instrument" + bytes(INSTRUMENT_FILE_HEADER_BYTES))


def test_every_key_the_instrument_routes_sounds_what_it_sounded(xm_song: Song) -> None:
    unit = InstrumentUnit(
        instrument=Instrument(name="split", keymap=keyed(sample=0)),
        samples=(voices_of(xm_song).samples[0],),
    )
    recovered = XMInstrumentFile.parse(instrument_file(unit).to_bytes()).unit
    for key in range(len(unit.instrument.keymap)):
        here = unit.instrument.assignment(Note(key))
        there = recovered.instrument.assignment(Note(key))
        assert (here is None) == (there is None)
        if here is not None and there is not None:
            assert here.note == there.note
            assert unit.samples[here.sample].name == recovered.samples[there.sample].name

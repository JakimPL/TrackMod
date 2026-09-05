from pathlib import Path

import numpy as np
import pytest

from tests.conftest import voices_of
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.keymap import routed_keymap
from trackmod.core.instruments.transfer import extract
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.core.notes.pitch import Note
from trackmod.core.songs.song import Song
from trackmod.limits.capability import Capability
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import LimitError
from trackmod.trackers.it.instrument_file import ITInstrumentFile
from trackmod.trackers.it.spec.identity import (
    CREATED_WITH,
    INSTRUMENT_EXTENSION,
    MAGIC_INSTRUMENT,
    MAGIC_SAMPLE,
)
from trackmod.trackers.it.spec.sizes import INSTRUMENT_HEADER_BYTES, SAMPLE_HEADER_BYTES

ROUTER = 1
STAGED_GAIN = 24
REFUSED_FADEOUT = 100_000
TRACKER_VERSION_AT = 28
TRACKER_VERSION_BYTES = 2
ENVELOPES_HERE_FROM = 0x0200  # the version from which an instrument keeps its envelopes where this writer puts them


def instrument_file(unit: InstrumentUnit, *, compliance: Compliance = Compliance.EXTENDED) -> ITInstrumentFile:
    return ITInstrumentFile.from_unit(unit, compliance=compliance)


def router(song: Song) -> InstrumentUnit:
    """The song's two-sample instrument, which is the unit these tests carry."""
    return extract(voices_of(song), ROUTER)


def test_the_file_opens_with_the_instrument_tag(song: Song) -> None:
    assert instrument_file(router(song)).to_bytes().startswith(MAGIC_INSTRUMENT)


def test_a_header_for_every_sample_follows_the_instrument(song: Song) -> None:
    unit = router(song)
    data = instrument_file(unit).to_bytes()
    for index in range(len(unit.samples)):
        at = INSTRUMENT_HEADER_BYTES + SAMPLE_HEADER_BYTES * index
        assert data[at : at + len(MAGIC_SAMPLE)] == MAGIC_SAMPLE


def test_the_size_model_agrees_with_the_written_file(song: Song) -> None:
    written = instrument_file(router(song))
    report = written.size()
    assert report.total == len(written.to_bytes())
    assert report.total == report.headers + report.pcm
    assert report.patterns == 0


def test_a_written_instrument_parses_back_to_the_same_voice(song: Song) -> None:
    original = router(song).instrument
    recovered = ITInstrumentFile.parse(instrument_file(router(song)).to_bytes()).unit.instrument
    assert recovered.name == original.name
    assert recovered.keymap == original.keymap
    assert recovered.volume_envelope == original.volume_envelope
    assert recovered.fadeout == original.fadeout
    assert recovered.new_note_action == original.new_note_action


def test_the_file_states_the_version_its_envelopes_are_laid_out_by(song: Song) -> None:
    # A module hands its loader the version its own file header carries; an instrument travelling alone
    # carries the only copy of it, and a reader taking this field for a 1.x instrument looks for the
    # envelopes where that version kept them and finds none.
    data = instrument_file(router(song)).to_bytes()
    stated = int.from_bytes(data[TRACKER_VERSION_AT : TRACKER_VERSION_AT + TRACKER_VERSION_BYTES], "little")
    assert stated == CREATED_WITH
    assert stated >= ENVELOPES_HERE_FROM


def test_the_waveforms_survive_a_round_trip(song: Song) -> None:
    unit = router(song)
    recovered = ITInstrumentFile.parse(instrument_file(unit).to_bytes()).unit
    for original, restored in zip(unit.samples, recovered.samples):
        assert restored.name == original.name
        assert restored.rate == original.rate
        assert restored.depth == original.depth
        assert restored.loop == original.loop
        assert np.allclose(restored.pcm, original.pcm, atol=1.5 / original.depth.scale)


def test_the_gain_a_sample_is_staged_with_travels_with_it(song: Song) -> None:
    # This format stores a per-sample multiplier, so a bank measured against one keeps its balance.
    unit = router(song)
    staged = unit.model_copy(
        update={"samples": tuple(sample.model_copy(update={"gain": STAGED_GAIN}) for sample in unit.samples)}
    )
    recovered = ITInstrumentFile.parse(instrument_file(staged).to_bytes()).unit
    assert [sample.gain for sample in recovered.samples] == [STAGED_GAIN] * len(unit.samples)


def test_an_instrument_reaching_no_sample_is_the_header_alone() -> None:
    reserved = InstrumentUnit(instrument=Instrument(name="", keymap=routed_keymap({})), samples=())
    data = instrument_file(reserved).to_bytes()
    assert len(data) == INSTRUMENT_HEADER_BYTES
    assert ITInstrumentFile.parse(data).unit == reserved


def test_a_file_saves_and_loads_under_its_own_extension(tmp_path: Path, song: Song) -> None:
    written = instrument_file(router(song))
    path = tmp_path / f"router{written.extension}"
    written.save(path)
    assert written.extension == INSTRUMENT_EXTENSION
    assert ITInstrumentFile.load(path).unit.instrument.name == router(song).instrument.name


def test_a_value_this_format_refuses_is_reported_before_anything_is_written(song: Song) -> None:
    unit = router(song)
    loud = unit.model_copy(update={"instrument": unit.instrument.model_copy(update={"fadeout": REFUSED_FADEOUT})})
    written = instrument_file(loud)
    (reported,) = written.violations()
    assert reported.capability is Capability.FADEOUT
    with pytest.raises(LimitError):
        written.to_bytes()


def test_parsing_something_that_is_not_an_instrument_raises() -> None:
    with pytest.raises(ValueError, match="Impulse Tracker instrument tag"):
        ITInstrumentFile.parse(b"not an instrument" + bytes(INSTRUMENT_HEADER_BYTES))


def test_a_key_naming_a_sample_the_file_leaves_out_is_refused(song: Song) -> None:
    # The count in the header is what says how many samples follow, so a file understating it describes
    # a keymap reaching past what it carries.
    data = bytearray(instrument_file(router(song)).to_bytes())
    data[30] = 1
    with pytest.raises(ValueError, match="names sample"):
        ITInstrumentFile.parse(bytes(data))


def test_every_key_the_instrument_routes_sounds_what_it_sounded(song: Song) -> None:
    unit = router(song)
    recovered = ITInstrumentFile.parse(instrument_file(unit).to_bytes()).unit
    for key in range(len(unit.instrument.keymap)):
        here = unit.instrument.assignment(Note(key))
        there = recovered.instrument.assignment(Note(key))
        assert (here is None) == (there is None)
        if here is not None and there is not None:
            assert here.note == there.note
            assert unit.samples[here.sample].name == recovered.samples[there.sample].name

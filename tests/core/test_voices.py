import numpy as np
import pytest

from tests.conftest import make_sample
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.keymap import (
    KeyAssignment,
    pitched_keymap,
    routed_keymap,
)
from trackmod.core.notes.pitch import Note
from trackmod.core.samples.sample import Sample
from trackmod.core.voices.convert import flattened, raised
from trackmod.core.voices.voices import InstrumentVoices, SampleVoices
from trackmod.spec.pitch import REFERENCE_RATE


def sampled() -> SampleVoices:
    """Two waveforms a cell names directly, which is what a sample-addressed song holds."""
    return SampleVoices(samples=(make_sample("lead", seed=1), make_sample("bass", seed=2)))


def test_a_sample_table_is_as_wide_as_the_samples_it_holds() -> None:
    voices = sampled()
    assert voices.slots == 2
    assert len(voices.samples) == 2


def test_an_instrument_table_is_as_wide_as_the_instruments_it_holds() -> None:
    voices = InstrumentVoices(
        instruments=(Instrument(name="one", keymap=pitched_keymap(sample=0)),),
        samples=(make_sample("lead"), make_sample("bass")),
    )
    assert voices.slots == 1
    assert len(voices.samples) == 2


def test_an_instrument_naming_a_sample_the_table_leaves_out_is_rejected() -> None:
    with pytest.raises(ValueError, match="names sample 1 of 1"):
        InstrumentVoices(
            instruments=(Instrument(name="one", keymap=pitched_keymap(sample=1)),),
            samples=(make_sample("lead"),),
        )


def test_raising_gives_each_sample_the_instrument_that_sounds_it() -> None:
    voices = sampled()
    raised_voices = raised(voices)
    assert raised_voices.slots == voices.slots
    assert raised_voices.samples == voices.samples
    for index, instrument in enumerate(raised_voices.instruments):
        assert instrument.name == voices.samples[index].name
        assert instrument.samples == (index,)
        assert instrument.assignment(Note(60)) == KeyAssignment(sample=index, note=Note(60))


def test_flattening_what_was_raised_states_the_same_table() -> None:
    voices = sampled()
    assert flattened(raised(voices)) == voices


def test_flattening_keeps_every_cell_naming_the_voice_it_named() -> None:
    lead, bass = make_sample("lead", seed=1), make_sample("bass", seed=2)
    voices = InstrumentVoices(
        instruments=(
            Instrument(name="second", keymap=pitched_keymap(sample=1)),
            Instrument(name="first", keymap=pitched_keymap(sample=0)),
        ),
        samples=(lead, bass),
    )
    assert flattened(voices).samples == (bass, lead)


def test_an_instrument_routing_no_key_flattens_to_an_empty_slot() -> None:
    voices = InstrumentVoices(
        instruments=(Instrument(name="reserved", keymap=routed_keymap({})),),
        samples=(make_sample("lead"),),
    )
    (placeholder,) = flattened(voices).samples
    assert placeholder.name == "reserved"
    assert placeholder.frames == 0
    assert placeholder.rate == REFERENCE_RATE


def test_an_instrument_reaching_two_samples_is_refused() -> None:
    voices = InstrumentVoices(
        instruments=(
            Instrument(
                name="router",
                keymap=routed_keymap(
                    {
                        Note(60): KeyAssignment(sample=0, note=Note(60)),
                        Note(61): KeyAssignment(sample=1, note=Note(61)),
                    }
                ),
            ),
        ),
        samples=(make_sample("lead"), make_sample("bass")),
    )
    with pytest.raises(ValueError, match="routes keys to 2 samples"):
        flattened(voices)


def test_an_instrument_sounding_a_key_at_another_pitch_is_refused() -> None:
    voices = InstrumentVoices(
        instruments=(
            Instrument(name="shifted", keymap=routed_keymap({Note(60): KeyAssignment(sample=0, note=Note(72))})),
        ),
        samples=(make_sample("lead"),),
    )
    with pytest.raises(ValueError, match="sounds key 60"):
        flattened(voices)


def test_a_placeholder_slot_carries_no_frames() -> None:
    empty = Sample(name="", pcm=np.zeros(0), rate=REFERENCE_RATE)
    assert flattened(raised(SampleVoices(samples=(empty,)))).samples == (empty,)

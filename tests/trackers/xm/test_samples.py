import numpy as np
import pytest

from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.sample import Sample
from trackmod.core.voices.voices import InstrumentVoices
from trackmod.trackers.xm.instruments.group import SampleGroup
from trackmod.trackers.xm.layout.sample import SAMPLE_HEADER
from trackmod.trackers.xm.samples.parser import parse_sample
from trackmod.trackers.xm.samples.writer import sample_bytes, sample_header
from trackmod.trackers.xm.spec.sizes import KEYMAP_NOTES
from trackmod.trackers.xm.tuning import Tuning

RATE = 44100
CENTRE_PANNING = 128  # the middle of the byte this format gives every sample its own place on
from trackmod.trackers.xm.spec.sizes import KEYMAP_NOTES


def test_relative_note_and_finetune_round_trip_through_the_header() -> None:
    sample = Sample(name="lead", pcm=np.zeros(8), rate=RATE)
    tuning = Tuning(relative_note=5, finetune=-30)

    header = sample_header(sample, tuning=tuning)
    values = SAMPLE_HEADER.unpack(header)
    recovered = parse_sample(values, sample_bytes(sample), subject="sample", repairs=Repairs())

    assert recovered.relative_note == tuning.relative_note
    assert recovered.finetune == tuning.finetune


def test_a_whole_semitone_tuning_carries_no_finetune_trim() -> None:
    sample = Sample(name="lead", pcm=np.zeros(8), rate=RATE)
    tuning = Tuning(relative_note=-12, finetune=0)

    header = sample_header(sample, tuning=tuning)
    values = SAMPLE_HEADER.unpack(header)
    recovered = parse_sample(values, sample_bytes(sample), subject="sample", repairs=Repairs())

    assert recovered.relative_note == -12
    assert recovered.finetune == 0


def test_a_sample_stating_no_place_of_its_own_is_written_to_the_middle_of_the_field() -> None:
    # Every sample record holds a panning byte whatever a song says about it, so the value a tracker
    # fills that byte with is what a sample carrying none is written at.
    sample = Sample(name="lead", pcm=np.zeros(8), rate=RATE)
    values = SAMPLE_HEADER.unpack(sample_header(sample, tuning=Tuning(relative_note=0, finetune=0)))

    assert sample.panning is None
    assert values["panning"] == CENTRE_PANNING


def test_a_group_holds_one_tuning_for_every_sample_it_carries(xm_voices: InstrumentVoices) -> None:
    with pytest.raises(ValueError, match="samples carry"):
        SampleGroup(samples=xm_voices.samples[:2], tunings=(), keymap=(0,) * KEYMAP_NOTES)


def test_a_group_keymap_covers_every_key_this_format_maps() -> None:
    with pytest.raises(ValueError, match="a keymap covers"):
        SampleGroup(samples=(), tunings=(), keymap=(0,))


def test_a_group_key_names_a_sample_the_group_carries(xm_voices: InstrumentVoices) -> None:
    tunings = (Tuning(relative_note=0, finetune=0),)
    with pytest.raises(ValueError, match="names sample 1 of 1"):
        SampleGroup(samples=xm_voices.samples[:1], tunings=tunings, keymap=(1,) * KEYMAP_NOTES)

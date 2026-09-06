import numpy as np

from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.sample import Sample
from trackmod.trackers.xm.layout.sample import SAMPLE_HEADER
from trackmod.trackers.xm.samples.parser import parse_sample
from trackmod.trackers.xm.samples.writer import sample_bytes, sample_header
from trackmod.trackers.xm.tuning import Tuning

RATE = 44100
CENTRE_PANNING = 128  # the middle of the byte this format gives every sample its own place on


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

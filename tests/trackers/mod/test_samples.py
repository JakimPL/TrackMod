import numpy as np
import pytest

from tests.conftest import lattice
from tests.trackers.mod.conftest import sample_record
from trackmod.binary.cursor import Cursor
from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.sample import Sample
from trackmod.spec.levels import MAX_VOLUME
from trackmod.spec.pitch import REFERENCE_RATE
from trackmod.trackers.mod.layout.sample import SAMPLE_HEADER
from trackmod.trackers.mod.samples.parser import parse_sample, stated_frames, stored_bytes
from trackmod.trackers.mod.samples.writer import (
    empty_header,
    sample_bytes,
    sample_header,
)
from trackmod.trackers.mod.samples.writer import stored_frames as stored_frame_count
from trackmod.trackers.mod.spec.defaults import NO_LOOP_LENGTH
from trackmod.trackers.mod.spec.periods import FINETUNE_RATES
from trackmod.trackers.mod.spec.sizes import WORD_BYTES


def written(sample: Sample) -> Sample:
    """The sample a record and its frames read back as, which is what a round trip has to preserve."""
    values = SAMPLE_HEADER.unpack(sample_header(sample))
    return parse_sample(values, sample_bytes(sample), subject="sample 0", repairs=Repairs())


def test_a_sample_reads_back_as_it_was_written(mod_samples: tuple[Sample, ...]) -> None:
    for sample in mod_samples:
        assert written(sample) == sample


def test_a_record_counts_its_lengths_in_pairs_of_frames() -> None:
    sample = Sample(
        name="looped",
        pcm=lattice(np.linspace(-1.0, 1.0, 48), BitDepth.EIGHT),
        rate=REFERENCE_RATE,
        depth=BitDepth.EIGHT,
        loop=Loop(begin=8, end=40, mode=LoopMode.FORWARD),
    )
    values = SAMPLE_HEADER.unpack(sample_header(sample))
    assert values["length"] == 48 // WORD_BYTES
    assert values["loop_begin"] == 8 // WORD_BYTES
    assert values["loop_length"] == 32 // WORD_BYTES
    assert stored_bytes(values) == 48


def test_a_sample_that_plays_through_once_states_the_shortest_loop() -> None:
    sample = Sample(
        name="plain",
        pcm=lattice(np.linspace(-1.0, 1.0, 16), BitDepth.EIGHT),
        rate=REFERENCE_RATE,
        depth=BitDepth.EIGHT,
    )
    values = SAMPLE_HEADER.unpack(sample_header(sample))
    assert values["loop_length"] == NO_LOOP_LENGTH
    assert written(sample).loop is None


def test_an_unfilled_slot_states_the_same_shortest_loop() -> None:
    values = SAMPLE_HEADER.unpack(empty_header())
    assert values["length"] == 0
    assert values["loop_length"] == NO_LOOP_LENGTH


def test_a_waveform_of_an_odd_length_is_closed_by_one_silent_frame() -> None:
    sample = Sample(
        name="odd",
        pcm=lattice(np.linspace(-1.0, 1.0, 33), BitDepth.EIGHT),
        rate=REFERENCE_RATE,
        depth=BitDepth.EIGHT,
    )
    assert stored_frame_count(33) == 34
    assert len(sample_bytes(sample)) == 34
    assert written(sample).frames == 34


def test_each_tuning_row_survives_the_record_that_states_it() -> None:
    for rate in FINETUNE_RATES:
        sample = Sample(
            name="tuned",
            pcm=lattice(np.linspace(-1.0, 1.0, 8), BitDepth.EIGHT),
            rate=rate,
            depth=BitDepth.EIGHT,
        )
        assert written(sample).rate == rate


def test_a_level_above_full_is_drawn_back_to_full() -> None:
    repairs = Repairs()
    values = SAMPLE_HEADER.unpack(sample_record(length=4, volume=200))
    sample = parse_sample(values, bytes(8), subject="sample 0", repairs=repairs)
    assert sample.volume == MAX_VOLUME
    assert repairs.entries == (("sample 0", f"volume 200 read as {MAX_VOLUME}"),)


def test_a_loop_past_the_waveform_is_drawn_inside_it() -> None:
    repairs = Repairs()
    values = SAMPLE_HEADER.unpack(sample_record(length=4, volume=64, loop_begin=1, loop_length=8))
    sample = parse_sample(values, bytes(8), subject="sample 0", repairs=repairs)
    assert sample.loop is not None
    assert sample.loop.end == sample.frames
    assert repairs.entries[0][0] == "sample 0"


def test_a_waveform_shorter_than_its_record_states_is_read_as_far_as_it_goes() -> None:
    repairs = Repairs()
    values = SAMPLE_HEADER.unpack(sample_record(length=8, volume=64))
    cursor = Cursor(bytes(6))
    frames = stated_frames(cursor, values, subject="sample 0", repairs=repairs)
    assert len(frames) == 6
    assert repairs.entries == (("sample 0", "waveform of 16 bytes read as the 6 the file holds"),)


def unstorable(**changes: object) -> Sample:
    stored = {
        "name": "probe",
        "pcm": lattice(np.linspace(-1.0, 1.0, 16), BitDepth.EIGHT),
        "rate": REFERENCE_RATE,
        "depth": BitDepth.EIGHT,
    }
    return Sample(**{**stored, **changes})


def test_a_sample_this_format_keeps_no_field_for_is_refused() -> None:
    stereo = lattice(np.linspace(-1.0, 1.0, 32), BitDepth.EIGHT).reshape(16, 2)
    refused = (
        (unstorable(pcm=stereo), "stereo"),
        (unstorable(depth=BitDepth.SIXTEEN, pcm=lattice(np.linspace(-1.0, 1.0, 16))), "stores eight"),
        (unstorable(panning=64), "panning"),
        (unstorable(sustain_loop=Loop(begin=0, end=8, mode=LoopMode.FORWARD)), "sustain loop"),
        (unstorable(loop=Loop(begin=0, end=8, mode=LoopMode.PING_PONG)), "loops forwards"),
    )
    for sample, reason in refused:
        with pytest.raises(ValueError, match=reason):
            sample_header(sample)

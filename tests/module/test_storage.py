import pytest

from trackmod.core.samples.depth import BitDepth
from trackmod.module.storage import Storage

TABLE = Storage(file=100, order=1, pattern=12, instrument=500, empty_instrument=20, sample=80)

SAMPLE_FRAMES = 1000


@pytest.mark.parametrize("depth", list(BitDepth))
def test_a_waveform_costs_its_frames_at_the_depth_it_is_stored_in(depth: BitDepth) -> None:
    assert TABLE.frames_bytes(frames=SAMPLE_FRAMES, depth=depth) == SAMPLE_FRAMES * depth.bytes_per_frame


def test_a_stored_sample_costs_its_records_on_top_of_its_frames() -> None:
    cost = TABLE.sample_bytes(frames=SAMPLE_FRAMES, depth=BitDepth.SIXTEEN)
    assert cost == TABLE.sample + 2 * SAMPLE_FRAMES


def test_a_deeper_sample_costs_more_only_in_its_frames() -> None:
    deep = TABLE.sample_bytes(frames=SAMPLE_FRAMES, depth=BitDepth.SIXTEEN)
    shallow = TABLE.sample_bytes(frames=SAMPLE_FRAMES, depth=BitDepth.EIGHT)
    assert deep - shallow == SAMPLE_FRAMES


def test_an_instrument_owning_nothing_is_charged_the_short_header() -> None:
    assert TABLE.instrument_bytes(samples=0) == TABLE.empty_instrument
    assert TABLE.instrument_bytes(samples=1) == TABLE.instrument


def test_the_overhead_sums_every_record_the_module_lays_out() -> None:
    overhead = TABLE.overhead(instruments=(2, 0), samples=2, patterns=3, orders=4)
    assert overhead == TABLE.file + 4 * TABLE.order + 3 * TABLE.pattern + TABLE.instrument + TABLE.empty_instrument + (
        2 * TABLE.sample
    )


def test_an_empty_module_still_costs_what_the_file_spends_before_any_content() -> None:
    assert TABLE.overhead(instruments=(), samples=0, patterns=0, orders=0) == TABLE.file


@pytest.mark.parametrize("depth", list(BitDepth))
def test_the_frame_budget_is_the_inverse_of_what_a_sample_costs(depth: BitDepth) -> None:
    budget = TABLE.sample_bytes(frames=SAMPLE_FRAMES, depth=depth)
    assert TABLE.frames_budget(budget, depth=depth) == SAMPLE_FRAMES
    assert TABLE.sample_bytes(frames=TABLE.frames_budget(budget, depth=depth), depth=depth) <= budget


def test_a_budget_too_small_for_the_records_buys_no_frames() -> None:
    assert TABLE.frames_budget(TABLE.sample, depth=BitDepth.SIXTEEN) == 0
    assert TABLE.frames_budget(0, depth=BitDepth.SIXTEEN) == 0

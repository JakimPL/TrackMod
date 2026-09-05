import pytest

from trackmod.core.volumes.command import VolumeCommand, VolumeEffect
from trackmod.spec.grid import EMPTY
from trackmod.trackers.s3m.spec.volume import PANNING_BASE
from trackmod.trackers.s3m.volume import (
    decode_volume,
    encode_volume,
    refusal,
    stored_byte,
    stored_volume,
)


def test_the_column_holds_a_level_across_the_range_a_sample_plays_at() -> None:
    assert stored_byte(0) == 0
    assert stored_byte(64) == 64
    assert decode_volume(48) == 48


def test_the_column_states_a_position_across_the_field_beside_its_levels() -> None:
    panning = VolumeCommand(effect=VolumeEffect.PANNING, amount=32)
    assert encode_volume(panning) == PANNING_BASE + 32
    assert decode_volume(PANNING_BASE + 32) == panning


def test_a_byte_between_the_two_runs_names_nothing_this_column_defines() -> None:
    assert decode_volume(100) is None
    assert decode_volume(200) is None


def test_a_command_this_column_has_no_run_for_is_refused_by_name() -> None:
    slide = VolumeCommand(effect=VolumeEffect.VIBRATO_DEPTH, amount=4)
    assert stored_byte(slide) is None
    assert "no run for VIBRATO_DEPTH" in refusal(slide)
    with pytest.raises(ValueError, match="no run for"):
        encode_volume(slide)


def test_an_amount_past_the_run_that_holds_it_is_refused() -> None:
    wide = VolumeCommand(effect=VolumeEffect.PANNING, amount=200)
    assert "amounts its run holds" in refusal(wide)
    with pytest.raises(ValueError, match="amounts its run holds"):
        encode_volume(wide)


def test_an_absent_volume_stays_absent_through_the_grid() -> None:
    assert stored_volume(EMPTY) == EMPTY
    assert stored_volume(48) == 48

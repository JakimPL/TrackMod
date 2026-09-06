import pytest

from trackmod.core.volumes.command import VolumeCommand, VolumeEffect
from trackmod.spec.grid import EMPTY
from trackmod.trackers.s3m.spec.volume import PANNING_BASE, VOLUME_COLUMN


def test_the_column_holds_a_level_across_the_range_a_sample_plays_at() -> None:
    assert VOLUME_COLUMN.stored(0) == 0
    assert VOLUME_COLUMN.stored(64) == 64
    assert VOLUME_COLUMN.stated(48) == 48


def test_the_column_states_a_position_across_the_field_beside_its_levels() -> None:
    panning = VolumeCommand(effect=VolumeEffect.PANNING, amount=32)
    assert VOLUME_COLUMN.encoded(panning) == PANNING_BASE + 32
    assert VOLUME_COLUMN.stated(PANNING_BASE + 32) == panning


def test_a_byte_between_the_two_runs_names_nothing_this_column_defines() -> None:
    assert VOLUME_COLUMN.stated(100) is None
    assert VOLUME_COLUMN.stated(200) is None


def test_a_command_this_column_has_no_run_for_is_refused_by_name() -> None:
    slide = VolumeCommand(effect=VolumeEffect.VIBRATO_DEPTH, amount=4)
    assert VOLUME_COLUMN.stored(slide) is None
    assert "no run for VIBRATO_DEPTH" in VOLUME_COLUMN.refusal(slide)
    with pytest.raises(ValueError, match="no run for"):
        VOLUME_COLUMN.encoded(slide)


def test_an_amount_past_the_run_that_holds_it_is_refused() -> None:
    wide = VolumeCommand(effect=VolumeEffect.PANNING, amount=200)
    assert "amounts its run holds" in VOLUME_COLUMN.refusal(wide)
    with pytest.raises(ValueError, match="amounts its run holds"):
        VOLUME_COLUMN.encoded(wide)


def test_an_absent_volume_stays_absent_through_the_grid() -> None:
    assert VOLUME_COLUMN.stored_code(EMPTY) == EMPTY
    assert VOLUME_COLUMN.stored_code(48) == 48

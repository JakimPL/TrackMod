import pytest

from trackmod.binary.nibble import split_nibbles
from trackmod.spec.width import NIBBLE_MAX
from trackmod.trackers.mod.effects.catalog import MOD_EFFECTS, extended
from trackmod.trackers.mod.effects.command import MODEffect, MODExtended
from trackmod.trackers.mod.spec.ranges import (
    MAX_EFFECT_SPEED,
    MAX_EFFECT_TEMPO,
    MIN_EFFECT_TEMPO,
    PATTERN_ROWS,
)

E8 = 0x8


def test_the_command_set_fills_the_nibble_a_cell_holds_it_in() -> None:
    assert {int(command) for command in MODEffect} == set(range(NIBBLE_MAX + 1))


def test_a_command_prints_the_character_a_tracker_shows() -> None:
    assert MODEffect.ARPEGGIO.letter == "0"
    assert MODEffect.VOLUME_SLIDE.letter == "A"
    assert MODEffect.SET_SPEED.letter == "F"


def test_the_one_sub_command_the_trackers_disagreed_about_is_left_unnamed() -> None:
    assert E8 not in {int(sub_command) for sub_command in MODExtended}


def test_speed_and_tempo_share_one_command_split_by_where_the_parameter_falls() -> None:
    # This is the split the whole lineage inherited, and it is why the tempo floor is exactly where the
    # speed ceiling stops: one byte carries both, and nothing else states either.
    speed = MOD_EFFECTS.set_speed(MAX_EFFECT_SPEED)
    tempo = MOD_EFFECTS.set_tempo(MIN_EFFECT_TEMPO)
    assert speed.command == tempo.command == MODEffect.SET_SPEED
    assert speed.parameter + 1 == tempo.parameter


def test_a_clock_outside_either_range_is_refused() -> None:
    with pytest.raises(ValueError, match="speed"):
        MOD_EFFECTS.set_speed(MAX_EFFECT_SPEED + 1)

    with pytest.raises(ValueError, match="tempo"):
        MOD_EFFECTS.set_tempo(MIN_EFFECT_TEMPO - 1)

    with pytest.raises(ValueError, match="tempo"):
        MOD_EFFECTS.set_tempo(MAX_EFFECT_TEMPO + 1)


def test_a_pattern_break_states_its_row_a_decimal_digit_to_a_nibble() -> None:
    assert MOD_EFFECTS.pattern_break(0).parameter == 0x00
    assert MOD_EFFECTS.pattern_break(16).parameter == 0x16
    assert MOD_EFFECTS.pattern_break(PATTERN_ROWS - 1).parameter == 0x63


def test_a_break_past_the_last_row_a_pattern_holds_is_refused() -> None:
    with pytest.raises(ValueError, match="row"):
        MOD_EFFECTS.pattern_break(PATTERN_ROWS)


def test_a_sub_command_is_carried_in_the_high_nibble_of_its_parameter() -> None:
    delay = MOD_EFFECTS.note_delay(3)
    assert delay.command == MODEffect.EXTENDED
    assert split_nibbles(delay.parameter) == (MODExtended.NOTE_DELAY, 3)
    assert MOD_EFFECTS.note_cut(5).parameter == extended(MODExtended.NOTE_CUT, 5).parameter


def test_a_sub_command_value_past_four_bits_is_refused() -> None:
    with pytest.raises(ValueError, match="delay"):
        MOD_EFFECTS.note_delay(NIBBLE_MAX + 1)


def test_a_volume_slide_runs_one_way() -> None:
    assert MOD_EFFECTS.volume_slide(up=4, down=0).parameter == 0x40
    assert MOD_EFFECTS.volume_slide(up=0, down=4).parameter == 0x04
    with pytest.raises(ValueError, match="one way"):
        MOD_EFFECTS.volume_slide(up=1, down=1)


def test_panning_is_stated_on_the_shared_scale() -> None:
    assert MOD_EFFECTS.set_panning(255).parameter == 255
    with pytest.raises(ValueError, match="panning"):
        MOD_EFFECTS.set_panning(256)


def test_a_jump_names_any_position_the_order_byte_reaches() -> None:
    assert MOD_EFFECTS.position_jump(255).parameter == 255
    with pytest.raises(ValueError, match="order"):
        MOD_EFFECTS.position_jump(256)

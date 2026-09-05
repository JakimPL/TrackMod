import pytest

from trackmod.binary.nibble import split_nibbles
from trackmod.spec.levels import CENTRE_PANNING, MAX_PANNING
from trackmod.trackers.s3m.effects.catalog import S3M_EFFECTS
from trackmod.trackers.s3m.effects.command import S3MEffect, S3MExtended
from trackmod.trackers.s3m.spec.ranges import POSITION_MAX


@pytest.mark.parametrize(
    ("command", "letter"),
    [
        (S3MEffect.SET_SPEED, "A"),
        (S3MEffect.POSITION_JUMP, "B"),
        (S3MEffect.PATTERN_BREAK, "C"),
        (S3MEffect.SAMPLE_OFFSET, "O"),
        (S3MEffect.EXTENDED, "S"),
        (S3MEffect.SET_TEMPO, "T"),
        (S3MEffect.GLOBAL_VOLUME, "V"),
        (S3MEffect.SET_PANNING, "X"),
    ],
)
def test_each_command_prints_the_letter_it_holds(command: S3MEffect, letter: str) -> None:
    assert command.letter == letter


def test_speed_and_tempo_take_a_command_each() -> None:
    assert S3M_EFFECTS.set_speed(6).command == S3MEffect.SET_SPEED
    assert S3M_EFFECTS.set_tempo(125).command == S3MEffect.SET_TEMPO
    assert S3M_EFFECTS.set_tempo(125).parameter == 125


def test_a_break_states_its_row_a_decimal_digit_to_a_nibble() -> None:
    assert S3M_EFFECTS.pattern_break(16).parameter == 0x16


def test_the_delay_and_cut_commands_ride_the_extended_effect() -> None:
    for effect, sub_command in (
        (S3M_EFFECTS.note_delay(3), S3MExtended.NOTE_DELAY),
        (S3M_EFFECTS.note_cut(2), S3MExtended.NOTE_CUT),
    ):
        assert effect.command == S3MEffect.EXTENDED
        assert split_nibbles(effect.parameter)[0] == sub_command


def test_a_slide_runs_one_way_at_a_time() -> None:
    assert S3M_EFFECTS.volume_slide(up=4, down=0).parameter == 0x40
    with pytest.raises(ValueError, match="runs one way"):
        S3M_EFFECTS.volume_slide(up=4, down=4)


def test_panning_counts_the_field_in_the_finer_of_the_two_grids_this_format_states() -> None:
    assert S3M_EFFECTS.set_panning(0).parameter == 0
    assert S3M_EFFECTS.set_panning(MAX_PANNING).parameter == POSITION_MAX
    assert S3M_EFFECTS.set_panning(CENTRE_PANNING).parameter == POSITION_MAX // 2


@pytest.mark.parametrize(
    ("call", "argument"),
    [("set_speed", 0), ("set_tempo", 8), ("note_delay", 16), ("pattern_break", 64), ("set_panning", 256)],
)
def test_a_parameter_past_the_room_this_format_leaves_it_is_refused(call: str, argument: int) -> None:
    with pytest.raises(ValueError):
        getattr(S3M_EFFECTS, call)(argument)


def test_a_jump_names_the_order_position_it_continues_at() -> None:
    effect = S3M_EFFECTS.position_jump(12)
    assert effect.command == S3MEffect.POSITION_JUMP
    assert effect.parameter == 12

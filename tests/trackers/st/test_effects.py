import pytest

from trackmod.trackers.st.effects.catalog import ST_EFFECTS
from trackmod.trackers.st.effects.command import STEffect

NAMED_COMMANDS = 7
BREAK_ROW = 16
JUMP_POSITION = 3
SPEED_TICKS = 6


def test_the_commands_this_format_numbers_fill_none_of_the_nibble_it_left_over() -> None:
    assert len(STEffect) == NAMED_COMMANDS
    assert {command.letter for command in STEffect} == {"0", "1", "2", "B", "C", "D", "F"}


def test_the_three_intents_this_format_covers_spell_its_own_bytes() -> None:
    assert ST_EFFECTS.set_speed(SPEED_TICKS).command == STEffect.SET_SPEED
    assert ST_EFFECTS.position_jump(JUMP_POSITION).parameter == JUMP_POSITION
    assert ST_EFFECTS.pattern_break(BREAK_ROW).parameter == 0x16


@pytest.mark.parametrize(
    ("intent", "argument"),
    [
        ("set_tempo", {"beats_per_minute": 140}),
        ("note_delay", {"ticks": 3}),
        ("note_cut", {"ticks": 3}),
        ("set_panning", {"position": 128}),
    ],
)
def test_an_intent_this_format_numbers_no_command_for_says_which_one_would_carry_it(
    intent: str,
    argument: dict[str, int],
) -> None:
    with pytest.raises(ValueError, match="numbers none for"):
        getattr(ST_EFFECTS, intent)(**argument)


def test_a_volume_slide_says_which_command_would_carry_it() -> None:
    with pytest.raises(ValueError, match="numbers none for"):
        ST_EFFECTS.volume_slide(up=1, down=0)


def test_a_speed_past_the_five_bits_a_player_reads_is_refused() -> None:
    with pytest.raises(ValueError, match="speed"):
        ST_EFFECTS.set_speed(0x20)

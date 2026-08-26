import pytest

from trackmod.core.volumes.codec import decode_volume, encode_volume
from trackmod.core.volumes.command import VolumeCommand, VolumeEffect, VolumeValue
from trackmod.limits.capability import Capability
from trackmod.spec.levels import MAX_VOLUME
from trackmod.spec.volumes import AMOUNT_COUNT, LEVEL_COUNT, MAX_AMOUNT

LEVELS = (0, 1, 32, MAX_VOLUME)
COMMANDS = tuple(
    VolumeCommand(effect=effect, amount=amount) for effect in VolumeEffect for amount in (0, 9, MAX_AMOUNT)
)


@pytest.mark.parametrize("volume", [*LEVELS, *COMMANDS], ids=str)
def test_volume_column_encoding_round_trips(volume: VolumeValue) -> None:
    assert decode_volume(encode_volume(volume)) == volume


def test_commands_encode_past_the_level_range() -> None:
    # A volume column holds either a level or a command in one integer, so the two must not collide.
    assert all(encode_volume(command) >= LEVEL_COUNT for command in COMMANDS)
    assert len({encode_volume(command) for command in COMMANDS}) == len(COMMANDS)


def test_each_effect_holds_a_run_of_its_own() -> None:
    runs = {encode_volume(VolumeCommand(effect=effect, amount=0)) for effect in VolumeEffect}
    assert len(runs) == len(VolumeEffect)
    assert min(runs) == LEVEL_COUNT
    assert max(runs) == LEVEL_COUNT + (len(VolumeEffect) - 1) * AMOUNT_COUNT


def test_a_level_encodes_as_itself() -> None:
    assert [encode_volume(level) for level in LEVELS] == list(LEVELS)


@pytest.mark.parametrize("code", [-1, LEVEL_COUNT + len(VolumeEffect) * AMOUNT_COUNT])
def test_a_code_naming_neither_a_level_nor_a_command_is_refused(code: int) -> None:
    with pytest.raises(ValueError):
        decode_volume(code)


@pytest.mark.parametrize("amount", [-1, MAX_AMOUNT + 1])
def test_an_amount_off_the_column_is_refused(amount: int) -> None:
    with pytest.raises(ValueError):
        VolumeCommand(effect=VolumeEffect.VOLUME_SLIDE_UP, amount=amount)


def test_panning_is_bounded_apart_from_the_rates_and_depths() -> None:
    # A format counts panning positions and command rates in different numbers, so each is its own quantity.
    assert VolumeEffect.PANNING.capability is Capability.VOLUME_PANNING
    assert {effect.capability for effect in VolumeEffect if effect is not VolumeEffect.PANNING} == {
        Capability.VOLUME_COMMAND
    }


def test_a_command_is_usable_as_a_key() -> None:
    command = VolumeCommand(effect=VolumeEffect.VIBRATO_DEPTH, amount=4)
    assert {command: "vibrato"}[VolumeCommand(effect=VolumeEffect.VIBRATO_DEPTH, amount=4)] == "vibrato"

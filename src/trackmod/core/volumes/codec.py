from trackmod.core.volumes.command import VolumeCommand, VolumeEffect, VolumeValue
from trackmod.spec.volumes import AMOUNT_COUNT, LEVEL_COUNT


def encode_volume(volume: VolumeValue) -> int:
    """The integer a volume column stores for ``volume``."""
    match volume:
        case VolumeCommand():
            return LEVEL_COUNT + volume.effect * AMOUNT_COUNT + volume.amount
        case int():
            return volume


def decode_volume(code: int) -> VolumeValue:
    """The level or command a volume column's integer stands for.

    Raises:
        ValueError: when ``code`` names neither a level nor a command.
    """
    if 0 <= code < LEVEL_COUNT:
        return code

    return decode_command(code)


def decode_command(code: int) -> VolumeCommand:
    """The command a volume column's integer past the level range stands for.

    Raises:
        ValueError: when ``code`` names no command.
    """
    effect, amount = divmod(code - LEVEL_COUNT, AMOUNT_COUNT)
    return VolumeCommand(effect=VolumeEffect(effect), amount=amount)

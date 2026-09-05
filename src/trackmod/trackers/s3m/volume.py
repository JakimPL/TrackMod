from trackmod.core.volumes.codec import decode_volume as decode_shared_volume
from trackmod.core.volumes.command import VolumeValue
from trackmod.spec.grid import EMPTY
from trackmod.trackers.s3m.spec.volume import VOLUME_COLUMN


def stored_byte(volume: VolumeValue) -> int | None:
    """The volume byte this format stores, or ``None`` when its column cannot state ``volume``."""
    return VOLUME_COLUMN.stored(volume)


def refusal(volume: VolumeValue) -> str:
    """Why this format's volume column cannot state ``volume``."""
    return VOLUME_COLUMN.refusal(volume)


def encode_volume(volume: VolumeValue) -> int:
    """The volume byte this format stores for a volume-column entry.

    Raises:
        ValueError: when the volume column cannot state ``volume``.
    """
    byte = stored_byte(volume)
    if byte is None:
        raise ValueError(refusal(volume))

    return byte


def decode_volume(byte: int) -> VolumeValue | None:
    """The volume-column entry a stored byte states, or ``None`` when it names nothing this format defines."""
    return VOLUME_COLUMN.stated(byte)


def stored_volume(code: int) -> int:
    """The volume byte a grid volume code is written as, leaving an absent volume absent.

    Raises:
        ValueError: when the code names a volume this format's volume column cannot state.
    """
    if code == EMPTY:
        return EMPTY

    return encode_volume(decode_shared_volume(code))

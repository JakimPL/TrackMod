from enum import IntEnum, IntFlag, unique
from typing import Final

END_OF_ROW: Final = 0x00
CHANNEL_MASK: Final = 0x1F

MARKER_BYTE: Final = 1
KEY_BYTES: Final = 2
VOLUME_BYTE: Final = 1
EFFECT_BYTES: Final = 2
ROW_TERMINATOR_BYTE: Final = 1


@unique
class CellMask(IntFlag):
    """The marker byte of a packed cell: which of its three groups of bytes follow the channel it names.

    The note and the sample it plays share one bit, so the pair is written together and a cell stating
    one of them states the byte the other would have filled.
    """

    KEY = 0x20
    VOLUME = 0x40
    EFFECT = 0x80


GROUP_BYTES: Final = {
    CellMask.KEY: KEY_BYTES,
    CellMask.VOLUME: VOLUME_BYTE,
    CellMask.EFFECT: EFFECT_BYTES,
}


@unique
class NoteByte(IntEnum):
    """The note-column values that carry no key: one silences the channel, the other states nothing."""

    CUT = 254
    ABSENT = 255


NO_SAMPLE: Final = 0
SAMPLE_OFFSET: Final = 1
NO_EFFECT: Final = 0

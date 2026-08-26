from typing import Final

from trackmod.spec.levels import MAX_VOLUME
from trackmod.spec.width import BYTE_MAX

PAN_CENTER: Final = 32
PAN_MAX: Final = 64
CHANNEL_VOLUME_FULL: Final = 64

MAX_VOLUME_COMMAND: Final = 9
MAX_VOLUME_PANNING: Final = MAX_VOLUME

MAX_GLOBAL_VOLUME: Final = 128
MAX_MIX_VOLUME: Final = 128

MAX_PATTERNS: Final = 200
CANONICAL_MAX_ORDERS: Final = 256

CANONICAL_MIN_ROWS: Final = 32
MAX_ROWS: Final = 200

CANONICAL_MAX_CHANNELS: Final = 64
EXTENDED_MAX_CHANNELS: Final = 127

MIN_SPEED: Final = 1
MAX_SPEED: Final = BYTE_MAX
MIN_TEMPO: Final = 32
MAX_TEMPO: Final = BYTE_MAX

MAX_C5_SPEED: Final = 9_999_999

CANONICAL_MAX_FADEOUT: Final = 128
FADE_COUNTER: Final = 1024

CANONICAL_MAX_MESSAGE_BYTES: Final = 8_000

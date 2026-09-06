from typing import Final

from trackmod.spec.width import BYTE_MAX
from trackmod.trackers.amiga.spec.cells import CELL_BYTES
from trackmod.trackers.amiga.spec.ranges import PATTERN_ROWS
from trackmod.trackers.st.spec.sizes import SAMPLE_SLOTS

CHANNELS: Final = 4

PATTERN_BYTES: Final = PATTERN_ROWS * CHANNELS * CELL_BYTES

MAX_PATTERNS: Final = BYTE_MAX + 1

MAX_SAMPLES: Final = SAMPLE_SLOTS

LOOP_BEGIN_UNIT: Final = 1

NO_RESTART: Final = 0

MIN_EFFECT_SPEED: Final = 1
MAX_EFFECT_SPEED: Final = 0x1F

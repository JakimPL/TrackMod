from typing import Final

from trackmod.spec.width import WORD_MAX
from trackmod.trackers.amiga.spec.defaults import NO_LOOP_LENGTH
from trackmod.trackers.amiga.spec.periods import FINETUNE_RATES
from trackmod.trackers.amiga.spec.sizes import ORDER_TABLE_BYTES, WORD_BYTES
from trackmod.trackers.amiga.spec.storage import PCM_DEPTH

PATTERN_ROWS: Final = 64
MAX_BREAK_ROW: Final = PATTERN_ROWS - 1

MAX_ORDERS: Final = ORDER_TABLE_BYTES

MAX_SAMPLE_BYTES: Final = WORD_MAX * WORD_BYTES
MAX_SAMPLE_FRAMES: Final = MAX_SAMPLE_BYTES // PCM_DEPTH.bytes_per_frame

MIN_LOOP_WORDS: Final = NO_LOOP_LENGTH + 1
MIN_LOOP_FRAMES: Final = MIN_LOOP_WORDS * WORD_BYTES

MIN_SAMPLE_RATE: Final = min(FINETUNE_RATES)
MAX_SAMPLE_RATE: Final = max(FINETUNE_RATES)

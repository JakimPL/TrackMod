from typing import Final

from trackmod.spec.pitch import NOTE_COUNT, NOTES_PER_OCTAVE, REFERENCE_RATE

TABULATED_OCTAVES: Final = (
    (856, 808, 762, 720, 678, 640, 604, 570, 538, 508, 480, 453),
    (428, 404, 381, 360, 339, 320, 302, 285, 269, 254, 240, 226),
    (214, 202, 190, 180, 170, 160, 151, 143, 135, 127, 120, 113),
)

AMIGA_PERIODS: Final = tuple(period for octave in TABULATED_OCTAVES for period in octave)

FINETUNE_ROWS: Final = (
    (856, 850, 844, 838, 832, 826, 820, 814),
    (907, 900, 894, 887, 881, 875, 868, 862),
)

FINETUNE_PERIODS: Final = tuple(period for row in FINETUNE_ROWS for period in row)
FINETUNE_COUNT: Final = len(FINETUNE_PERIODS)
FINETUNE_RATES: Final = tuple(round(REFERENCE_RATE * AMIGA_PERIODS[0] / period) for period in FINETUNE_PERIODS)

BASE_NOTE: Final = 48
BASE_OCTAVES: Final = len(TABULATED_OCTAVES)
TOP_OCTAVE: Final = len(AMIGA_PERIODS) - NOTES_PER_OCTAVE

PERIOD_BITS: Final = 12
MAX_PERIOD: Final = (1 << PERIOD_BITS) - 1

MIN_NOTE: Final = 21
MAX_NOTE: Final = NOTE_COUNT - 1

CANONICAL_MIN_NOTE: Final = BASE_NOTE
CANONICAL_MAX_NOTE: Final = BASE_NOTE + len(AMIGA_PERIODS) - 1

HALF_SEMITONE: Final = 2 ** (1 / (2 * NOTES_PER_OCTAVE))

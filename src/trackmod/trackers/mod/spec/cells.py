from typing import Final

from trackmod.spec.width import NIBBLE_BITS, NIBBLE_MAX

CELL_BYTES: Final = 4
UNSTORABLE: Final = -1

PERIOD_HIGH_MASK: Final = NIBBLE_MAX
PERIOD_HIGH_BITS: Final = 8

SAMPLE_HIGH_MASK: Final = 0xF0
SAMPLE_SHIFT: Final = NIBBLE_BITS

COMMAND_MASK: Final = NIBBLE_MAX

NO_PERIOD: Final = 0
NO_SAMPLE: Final = 0
SAMPLE_OFFSET: Final = 1
NO_EFFECT: Final = 0

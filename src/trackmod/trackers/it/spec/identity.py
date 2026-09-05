from typing import Final

EXTENSION: Final = ".it"
INSTRUMENT_EXTENSION: Final = ".iti"

MAGIC_MODULE: Final = b"IMPM"
MAGIC_SAMPLE: Final = b"IMPS"
MAGIC_INSTRUMENT: Final = b"IMPI"

CREATED_WITH: Final = 0x0214

TRACKER_BITS: Final = 12  # the bits a created-with field spends on its version, below the program's own number
VERSION_MASK: Final = (1 << TRACKER_BITS) - 1
COMPATIBLE_WITH: Final = 0x0214

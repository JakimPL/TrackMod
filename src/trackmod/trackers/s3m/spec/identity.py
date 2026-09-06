from typing import Final

EXTENSION: Final = ".s3m"

MAGIC_MODULE: Final = b"SCRM"
MAGIC_SAMPLE: Final = b"SCRS"

MODULE_TYPE: Final = 16
END_OF_TEXT: Final = 0x1A

CREATED_WITH: Final = 0x1320

TRACKER_BITS: Final = 12  # the bits a created-with field spends on its version, below the program's own number
VERSION_MASK: Final = (1 << TRACKER_BITS) - 1

SIGNED_FRAMES: Final = 1
UNSIGNED_FRAMES: Final = 2

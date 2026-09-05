from typing import Final

from trackmod.binary.pcm.encoding import PcmEncoding
from trackmod.binary.pcm.sign import PcmSign
from trackmod.module.storage import Storage
from trackmod.trackers.it.spec.orders import ORDER_TERMINATOR_BYTES
from trackmod.trackers.it.spec.sizes import (
    FILE_HEADER_BYTES,
    INSTRUMENT_HEADER_BYTES,
    OFFSET_TABLE_ENTRY_BYTES,
    PATTERN_HEADER_BYTES,
    SAMPLE_HEADER_BYTES,
)

PCM_ENCODING: Final = PcmEncoding.ABSOLUTE
PCM_SIGN: Final = PcmSign.SIGNED

ORDER_BYTES: Final = 1

IT_STORAGE: Final = Storage(
    file=FILE_HEADER_BYTES + ORDER_TERMINATOR_BYTES,
    order=ORDER_BYTES,
    pattern=PATTERN_HEADER_BYTES + OFFSET_TABLE_ENTRY_BYTES,
    instrument=INSTRUMENT_HEADER_BYTES + OFFSET_TABLE_ENTRY_BYTES,
    empty_instrument=INSTRUMENT_HEADER_BYTES + OFFSET_TABLE_ENTRY_BYTES,
    sample=SAMPLE_HEADER_BYTES + OFFSET_TABLE_ENTRY_BYTES,
)

from typing import Final

from trackmod.binary.pcm.encoding import PcmEncoding
from trackmod.binary.pcm.sign import PcmSign
from trackmod.module.storage import Storage
from trackmod.trackers.xm.spec.sizes import (
    EMPTY_INSTRUMENT_HEADER_BYTES,
    FILE_HEADER_BYTES,
    INSTRUMENT_HEADER_BYTES,
    ORDER_TABLE_BYTES,
    PATTERN_HEADER_BYTES,
    SAMPLE_HEADER_BYTES,
)

PCM_ENCODING: Final = PcmEncoding.DELTA
PCM_SIGN: Final = PcmSign.SIGNED

ORDER_BYTES: Final = 0

XM_STORAGE: Final = Storage(
    file=FILE_HEADER_BYTES + ORDER_TABLE_BYTES,
    order=ORDER_BYTES,
    pattern=PATTERN_HEADER_BYTES,
    instrument=INSTRUMENT_HEADER_BYTES,
    empty_instrument=EMPTY_INSTRUMENT_HEADER_BYTES,
    sample=SAMPLE_HEADER_BYTES,
)

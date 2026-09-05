from typing import Final

from trackmod.binary.pcm.encoding import PcmEncoding
from trackmod.binary.pcm.sign import PcmSign
from trackmod.module.storage import Storage
from trackmod.trackers.s3m.spec.sizes import (
    CHANNELS_STORED,
    FILE_HEADER_BYTES,
    INSTRUMENT_RECORD_BYTES,
    ORDER_BYTES,
    PARAPOINTER_BYTES,
    PATTERN_LENGTH_BYTES,
)

PCM_ENCODING: Final = PcmEncoding.ABSOLUTE
PCM_SIGN: Final = PcmSign.UNSIGNED

NO_RECORD: Final = 0

S3M_STORAGE: Final = Storage(
    file=FILE_HEADER_BYTES + CHANNELS_STORED,
    order=ORDER_BYTES,
    pattern=PARAPOINTER_BYTES + PATTERN_LENGTH_BYTES,
    instrument=NO_RECORD,
    empty_instrument=NO_RECORD,
    sample=PARAPOINTER_BYTES + INSTRUMENT_RECORD_BYTES,
)

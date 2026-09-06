from typing import Final

from trackmod.binary.pcm.encoding import PcmEncoding
from trackmod.binary.pcm.sign import PcmSign
from trackmod.core.samples.depth import BitDepth
from trackmod.module.storage import Storage
from trackmod.trackers.mod.spec.sizes import FILE_HEADER_BYTES, WORD_BYTES

PCM_ENCODING: Final = PcmEncoding.ABSOLUTE
PCM_SIGN: Final = PcmSign.SIGNED
PCM_DEPTH: Final = BitDepth.EIGHT

NO_RECORD: Final = 0

MOD_STORAGE: Final = Storage(
    file=FILE_HEADER_BYTES,
    order=NO_RECORD,
    pattern=NO_RECORD,
    instrument=NO_RECORD,
    empty_instrument=NO_RECORD,
    sample=NO_RECORD,
    alignment=WORD_BYTES,
)

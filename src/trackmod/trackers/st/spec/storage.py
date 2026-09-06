from typing import Final

from trackmod.module.storage import Storage
from trackmod.trackers.amiga.spec.sizes import WORD_BYTES
from trackmod.trackers.st.spec.sizes import FILE_HEADER_BYTES

NO_RECORD: Final = 0

ST_STORAGE: Final = Storage(
    file=FILE_HEADER_BYTES,
    order=NO_RECORD,
    pattern=NO_RECORD,
    instrument=NO_RECORD,
    empty_instrument=NO_RECORD,
    sample=NO_RECORD,
    alignment=WORD_BYTES,
)

from trackmod.binary.cursor import Cursor
from trackmod.binary.records.values import read_bytes
from trackmod.trackers.amiga.layout.sample import SAMPLE_HEADER
from trackmod.trackers.amiga.samples.parser import stored_bytes
from trackmod.trackers.amiga.spec.sizes import SAMPLE_TABLE_OFFSET
from trackmod.trackers.st.layout.file import SEQUENCE
from trackmod.trackers.st.spec.ranges import PATTERN_BYTES
from trackmod.trackers.st.spec.sizes import FILE_HEADER_BYTES, SAMPLE_SLOTS


def stated_size(data: bytes) -> int | None:
    """How long a file stating this header would be, or ``None`` where the data stops inside the header.

    The header is a fixed slab and everything after it is found by walking what came before: every
    pattern the order table reaches at the one size a pattern takes, then every waveform its own record
    states the length of.
    """
    if len(data) < FILE_HEADER_BYTES:
        return None

    table = Cursor(data)
    table.seek(SAMPLE_TABLE_OFFSET)
    waveforms = sum(stored_bytes(table.read(SAMPLE_HEADER)) for _ in range(SAMPLE_SLOTS))
    sequence = SEQUENCE.unpack(data[FILE_HEADER_BYTES - SEQUENCE.size : FILE_HEADER_BYTES])
    patterns = max(read_bytes(sequence, "orders")) + 1
    return FILE_HEADER_BYTES + patterns * PATTERN_BYTES + waveforms


def written_here(data: bytes) -> bool:
    """Whether the bytes hold a module of this format, which is what its own records add up to.

    This format carries no tag and no magic, so the arithmetic is the whole of what a reader has: the
    fifteen records state how much waveform the file ends with, the order table names the last pattern
    before it, and a file of this format is exactly as long as the two come to behind its header.
    """
    return stated_size(data) == len(data)

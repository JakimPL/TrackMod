from trackmod.spec.width import BITS_PER_BYTE, WORD_MAX
from trackmod.trackers.s3m.spec.sizes import PARAGRAPH_BYTES

WAVEFORM_SHIFT = BITS_PER_BYTE * 2
LOW_WORD_MASK = WORD_MAX


def parapointer(offset: int) -> int:
    """The paragraph number a record sitting at ``offset`` is found by.

    Every table in this format points at sixteen-byte paragraphs rather than bytes, which is what lets a
    two-byte entry reach a megabyte into the file.

    Raises:
        ValueError: when the offset sits inside a paragraph rather than on one.
    """
    paragraph, inside = divmod(offset, PARAGRAPH_BYTES)
    if inside:
        raise ValueError(f"offset {offset} sits {inside} bytes into a paragraph, and a pointer names whole ones")

    return paragraph


def pointed(pointer: int) -> int:
    """Where the paragraph a pointer names begins."""
    return pointer * PARAGRAPH_BYTES


def split_pointer(offset: int) -> tuple[int, int]:
    """The high byte and low word an instrument record states its waveform's paragraph in.

    A waveform sits past everything else the file holds, so its pointer is given a third byte and reaches
    twenty-four bits where the record and pattern tables reach sixteen.

    Raises:
        ValueError: when the offset sits inside a paragraph rather than on one.
    """
    paragraph = parapointer(offset)
    return paragraph >> WAVEFORM_SHIFT, paragraph & LOW_WORD_MASK


def joined_pointer(high: int, low: int) -> int:
    """Where the waveform a record's two pointer fields name begins."""
    return pointed((high << WAVEFORM_SHIFT) | low)

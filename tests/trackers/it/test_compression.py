import numpy as np
import pytest

from tests.trackers.it.conftest import BitWriter, stated
from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.depth import BitDepth
from trackmod.trackers.it.samples.compression import BLOCK_FRAMES, decompress

WIDE_MARKER = {BitDepth.EIGHT: 1 << 8, BitDepth.SIXTEEN: 1 << 16}
SUBJECT = "sample 0"


@pytest.mark.parametrize("depth", list(BitDepth))
def test_a_block_reads_its_fields_as_the_differences_of_a_running_sum(depth: BitDepth) -> None:
    differences = [10, -3, 5, 0, -12]
    frames = decompress(
        stated(differences, depth=depth),
        frames=len(differences),
        depth=depth,
        doubled=False,
        subject=SUBJECT,
        repairs=Repairs(),
    )
    assert frames.tolist() == np.cumsum(differences).tolist()


@pytest.mark.parametrize("depth", list(BitDepth))
def test_the_later_compressor_sums_a_second_time(depth: BitDepth) -> None:
    differences = [4, 1, -2, 3]
    frames = decompress(
        stated(differences, depth=depth),
        frames=len(differences),
        depth=depth,
        doubled=True,
        subject=SUBJECT,
        repairs=Repairs(),
    )
    assert frames.tolist() == np.cumsum(np.cumsum(differences)).tolist()


@pytest.mark.parametrize("depth", list(BitDepth))
def test_a_field_announcing_a_narrower_width_reads_the_rest_at_it(depth: BitDepth) -> None:
    # At its opening width a field with the depth's own bit set names the width the block goes on at.
    writer = BitWriter()
    opening = int(depth) + 1
    writer.put(WIDE_MARKER[depth] | (4 - 1), opening)
    for difference in (3, -4, 1):
        writer.put(difference & 0b1111, 4)

    frames = decompress(writer.block(), frames=3, depth=depth, doubled=False, subject=SUBJECT, repairs=Repairs())
    assert frames.tolist() == [3, -1, 0]


def test_a_field_in_the_middle_range_announces_a_width_too() -> None:
    # Between seven bits and the depth's own width, a band above the values announces the next width.
    writer = BitWriter()
    writer.put(WIDE_MARKER[BitDepth.EIGHT] | (8 - 1), 9)
    writer.put(125, 8)
    for difference in (0b01, 0b11):
        writer.put(difference, 2)

    frames = decompress(
        writer.block(), frames=2, depth=BitDepth.EIGHT, doubled=False, subject=SUBJECT, repairs=Repairs()
    )
    assert frames.tolist() == [1, 0]


def test_a_waveform_longer_than_one_block_reads_across_them() -> None:
    depth = BitDepth.SIXTEEN
    span = BLOCK_FRAMES[depth]
    differences = [1] * span + [-1] * 8
    data = stated(differences[:span], depth=depth) + stated(differences[span:], depth=depth)
    frames = decompress(data, frames=len(differences), depth=depth, doubled=False, subject=SUBJECT, repairs=Repairs())
    assert frames[span - 1] == span
    # Each block opens its own running sum, so the second block counts down from its own first difference.
    assert frames[span:].tolist() == list(range(-1, -9, -1))


def test_a_waveform_of_no_frames_reads_as_nothing() -> None:
    assert decompress(b"", frames=0, depth=BitDepth.EIGHT, doubled=False, subject=SUBJECT, repairs=Repairs()).size == 0


def test_a_narrow_field_announces_the_next_width_in_a_field_of_its_own() -> None:
    # Below seven bits the announcement is the top bit alone, and the width follows in its own field.
    writer = BitWriter()
    writer.put(WIDE_MARKER[BitDepth.EIGHT] | (4 - 1), 9)
    writer.put(1 << 3, 4)
    writer.put(1, 3)
    for difference in (0b01, 0b11):
        writer.put(difference, 2)

    frames = decompress(
        writer.block(), frames=2, depth=BitDepth.EIGHT, doubled=False, subject=SUBJECT, repairs=Repairs()
    )
    assert frames.tolist() == [1, 0]


def test_a_block_announcing_a_width_its_depth_leaves_no_room_for_ends_there() -> None:
    # Files in the wild carry such a width, and a player sounds the frames before it and silence after.
    writer = BitWriter()
    writer.put(WIDE_MARKER[BitDepth.EIGHT] | 0xFF, 9)
    writer.put(0, 8)
    repairs = Repairs()
    frames = decompress(writer.block(), frames=1, depth=BitDepth.EIGHT, doubled=False, subject=SUBJECT, repairs=repairs)
    assert frames.tolist() == [0]
    assert repairs.entries == ((SUBJECT, "1 frames past a block's fields read as silence"),)

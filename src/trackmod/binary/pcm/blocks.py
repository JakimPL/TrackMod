from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.sample import STEREO_CHANNELS


def whole_frames(block: bytes, *, depth: BitDepth) -> bytes:
    """The head of a stored block that holds whole frames, which is as far as a cut-short block sounds."""
    return block[: len(block) - len(block) % depth.bytes_per_frame]


def paired_channels(data: bytes, *, block: int, depth: BitDepth) -> tuple[bytes, bytes]:
    """The two channel blocks of a stereo waveform, each read as far as both of them reach.

    A stereo waveform holds each channel's frames in full, the left before the right, so a file stopping
    inside the block holds all of the left channel and a part of the right. One frame is the pair of
    amplitudes a player sounds together, so both channels are read to the length they share.
    """
    left = whole_frames(data[:block], depth=depth)
    right = whole_frames(data[block : block * STEREO_CHANNELS], depth=depth)
    held = min(len(left), len(right))
    return left[:held], right[:held]

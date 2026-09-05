import numpy as np
from numpy.typing import NDArray

from trackmod.binary.pcm.encoding import PcmEncoding
from trackmod.binary.pcm.quantise import dequantise, quantise
from trackmod.binary.pcm.sign import PcmSign, bias, dtype_for
from trackmod.core.samples.depth import BitDepth


def encode_pcm(
    pcm: NDArray[np.float64],
    *,
    depth: BitDepth,
    encoding: PcmEncoding,
    sign: PcmSign,
) -> bytes:
    """Serialise float PCM in ``[-1, 1]`` to stored frames.

    The amplitudes are placed in the stored range before they are differenced, which is the order the
    two axes compose in: a player integrates in the width it reads, so the differences it sums are
    between the values that width holds.

    Deltas are taken in a width wider than the store and cast back, so a difference that overshoots the
    stored range wraps exactly as the player's running sum unwraps it. The first stored delta is taken
    against zero, which makes it the waveform's first stored amplitude.
    """
    amplitudes = quantise(pcm, depth) + bias(depth, sign=sign)
    match encoding:
        case PcmEncoding.ABSOLUTE:
            stored = amplitudes
        case PcmEncoding.DELTA:
            stored = np.diff(amplitudes, prepend=0)

    return stored.astype(dtype_for(depth, sign=sign)).tobytes()


def decode_pcm(
    data: bytes,
    *,
    depth: BitDepth,
    encoding: PcmEncoding,
    sign: PcmSign,
) -> NDArray[np.float64]:
    """Read stored frames back as float PCM in ``[-1, 1]``."""
    dtype = dtype_for(depth, sign=sign)
    stored = np.frombuffer(data, dtype=dtype)
    match encoding:
        case PcmEncoding.ABSOLUTE:
            frames = stored
        case PcmEncoding.DELTA:
            frames = np.cumsum(stored, dtype=dtype)

    return dequantise(frames.astype(np.int64) - bias(depth, sign=sign), depth)

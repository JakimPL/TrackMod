import numpy as np
from numpy.typing import NDArray

from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.loop import Loop
from trackmod.spec.pitch import REFERENCE_RATE


def repaired_loop(
    loop: Loop | None,
    *,
    frames: int,
    name: str,
    subject: str,
    repairs: Repairs,
) -> Loop | None:
    """A stored loop drawn inside the frames the waveform holds.

    A tracker states a loop as a pair of frame positions, and files carry pairs reaching past the frames
    that were stored -- most often where a waveform was shortened and its loop left as it was. The end
    is drawn back to the last frame and the begin to the end; a loop left with nothing between its ends
    repeats nothing, which is a sample that plays once.
    """
    if loop is None:
        return None

    end = min(loop.end, frames)
    begin = min(loop.begin, end)
    if (begin, end) == (loop.begin, loop.end):
        return loop

    repairs.made(f"{name} {loop.begin}..{loop.end} drawn to {begin}..{end} of {frames} frames", subject=subject)
    return Loop(begin=begin, end=end, mode=loop.mode) if end > begin else None


def repaired_rate(rate: int, *, subject: str, repairs: Repairs) -> int:
    """A stored playback rate, or the reference rate where a file states none.

    A rate of zero leaves a sample no pitch to sound at, so it is read as the rate the tracker lineage
    measures middle C by.
    """
    if rate > 0:
        return rate

    repairs.made(f"rate 0 read as {REFERENCE_RATE} Hz", subject=subject)
    return REFERENCE_RATE


def repaired_waveform(
    pcm: NDArray[np.float64],
    *,
    stated: int,
    subject: str,
    repairs: Repairs,
) -> NDArray[np.float64]:
    """The frames a waveform holds, reported where a record states more than the file goes on to carry.

    A record counts its frames per channel, so a file cut short in transit holds the head of a waveform
    while its record still states the whole of it. The frames that are there are the ones that sound,
    and the count they were read as is recorded.
    """
    held = int(pcm.shape[0])
    if held < stated:
        repairs.made(f"waveform of {stated} frames read as the {held} the file holds", subject=subject)

    return pcm

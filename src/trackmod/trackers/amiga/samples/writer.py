from typing import Final

import numpy as np

from trackmod.binary.pcm.codec import encode_pcm
from trackmod.binary.text import encode_name
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.sample import STEREO_CHANNELS, Sample
from trackmod.trackers.amiga.layout.sample import SAMPLE_HEADER
from trackmod.trackers.amiga.spec.defaults import NO_FINETUNE, NO_LOOP_LENGTH
from trackmod.trackers.amiga.spec.ranges import MIN_LOOP_FRAMES
from trackmod.trackers.amiga.spec.sizes import NAME_BYTES, WORD_BYTES
from trackmod.trackers.amiga.spec.storage import PCM_DEPTH, PCM_ENCODING, PCM_SIGN
from trackmod.trackers.amiga.tuning import finetune_for

NO_LENGTH: Final = 0
NO_BEGIN: Final = 0
SILENT_FRAME: Final = 0.0


def stored_frames(frames: int) -> int:
    """How many frames a waveform occupies once stored, which this lineage counts in pairs."""
    return frames + frames % WORD_BYTES


def stored_bytes(sample: Sample) -> int:
    """How many bytes a waveform occupies once stored, at the one depth this lineage writes."""
    return stored_frames(sample.frames) * PCM_DEPTH.bytes_per_frame


def reject_unstorable(sample: Sample) -> None:
    """Refuse to serialise a sample this lineage has no records for.

    Raises:
        ValueError: when the sample is stereo, stored at sixteen bits, panned, or carries a sustain loop,
            a loop that plays backwards, or a loop over a waveform of a single pair of frames — each of
            which this lineage keeps no field for.
    """
    if sample.channels == STEREO_CHANNELS:
        raise ValueError(f"sample {sample.name!r} is stereo, and this format stores one channel")

    if sample.depth is not PCM_DEPTH:
        raise ValueError(f"sample {sample.name!r} is stored at {int(sample.depth)} bits, and this format stores eight")

    if sample.panning is not None:
        raise ValueError(f"sample {sample.name!r} carries a panning, and this format stores none per sample")

    if sample.sustain_loop is not None:
        raise ValueError(f"sample {sample.name!r} carries a sustain loop, which this format cannot store")

    if sample.loop is not None and sample.loop.mode is not LoopMode.FORWARD:
        raise ValueError(f"sample {sample.name!r} loops {sample.loop.mode}, and this format loops forwards")

    if sample.loop is not None and stored_frames(sample.frames) < MIN_LOOP_FRAMES:
        raise ValueError(
            f"sample {sample.name!r} loops over {sample.frames} frames, "
            f"and a loop here runs for {MIN_LOOP_FRAMES} frames at the least"
        )


def sample_bytes(sample: Sample) -> bytes:
    """Serialise a waveform as this lineage stores it: one channel of signed frames, as they sound.

    A waveform of an odd length is closed by one silent frame, because a record counts its length in
    pairs of frames.
    """
    reject_unstorable(sample)
    padding = stored_frames(sample.frames) - sample.frames
    pcm = np.concatenate([sample.pcm, np.full(padding, SILENT_FRAME)]) if padding else sample.pcm
    return encode_pcm(pcm, depth=PCM_DEPTH, encoding=PCM_ENCODING, sign=PCM_SIGN)


def stored_loop(loop: Loop, *, frames: int, begin_unit: int) -> tuple[int, int]:
    """Where a loop begins and how far it runs, as the two fields of a record count them.

    The beginning is taken back to the unit holding it and the end on to the pair closing it, so every
    frame a loop repeats stays inside the region the record names. A record says a sample plays through
    once by running its loop for a single pair, so a loop runs for two at the least and is drawn back
    into the waveform to make the room.
    """
    stored = stored_frames(frames)
    end = min(max(stored_frames(loop.end), MIN_LOOP_FRAMES), stored)
    reach = max(min(loop.begin, end - MIN_LOOP_FRAMES), NO_BEGIN)
    begin = reach - reach % begin_unit
    return begin // begin_unit, (end - begin) // WORD_BYTES


def sample_header(sample: Sample, *, begin_unit: int) -> bytes:
    """Serialise a sample record, whose stored length counts pairs of frames."""
    reject_unstorable(sample)
    loop = sample.loop
    begin, length = (
        (NO_BEGIN, NO_LOOP_LENGTH) if loop is None else stored_loop(loop, frames=sample.frames, begin_unit=begin_unit)
    )
    return SAMPLE_HEADER.pack(
        {
            "name": encode_name(sample.name, NAME_BYTES),
            "length": stored_frames(sample.frames) // WORD_BYTES,
            "finetune": finetune_for(sample.rate),
            "volume": sample.volume,
            "loop_begin": begin,
            "loop_length": length,
        }
    )


def empty_header() -> bytes:
    """Serialise the record of a slot holding no waveform, which every module writes all of."""
    return SAMPLE_HEADER.pack(
        {
            "name": encode_name("", NAME_BYTES),
            "length": NO_LENGTH,
            "finetune": NO_FINETUNE,
            "volume": 0,
            "loop_begin": NO_BEGIN,
            "loop_length": NO_LOOP_LENGTH,
        }
    )

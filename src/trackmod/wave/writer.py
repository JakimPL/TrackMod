from pathlib import Path
from typing import Final

import numpy as np

from trackmod.binary.pcm.codec import encode_pcm
from trackmod.binary.text import encode_name, encode_text
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.sample import Sample
from trackmod.spec.levels import CENTRE_PANNING
from trackmod.spec.pitch import RATE_NOTE
from trackmod.wave.chunks import tagged, wrapped
from trackmod.wave.layout import (
    EXTRA_CHUNK,
    FORMAT_CHUNK,
    INSTRUMENT_CHUNK,
    SAMPLER_CHUNK,
    SAMPLER_LOOP,
)
from trackmod.wave.spec import (
    DATA_TAG,
    DEFAULT_WAVEFORM,
    EXTRA_TAG,
    FILENAME_BYTES,
    FORMAT_TAG,
    FORWARD_LOOP,
    HIGHEST_KEY,
    INFO_FORM,
    INSTRUMENT_TAG,
    INTEGER_SAMPLES,
    LIST_TAG,
    LOOPS_FOREVER,
    LOUDEST_VELOCITY,
    LOWEST_KEY,
    NAME_BYTES,
    NAME_TAG,
    NANOSECONDS,
    NO_FINETUNE,
    NO_GAIN,
    PANNING_SET,
    PING_PONG_LOOP,
    SAMPLER_TAG,
    SOFTEST_VELOCITY,
    STORED_ENCODING,
    STORED_SIGNS,
    STORED_VOLUME_SCALE,
    STORED_WAVEFORMS,
)

NO_FLAGS: Final = 0
NO_LOOP: Final = SAMPLER_LOOP.pack(
    {
        "identifier": 0,
        "mode": FORWARD_LOOP,
        "begin": 0,
        "end": 0,
        "fraction": 0,
        "plays": LOOPS_FOREVER,
    }
)
INSTRUMENT_RECORD: Final = INSTRUMENT_CHUNK.pack(
    {
        "unshifted_note": RATE_NOTE,
        "finetune": NO_FINETUNE,
        "gain": NO_GAIN,
        "low_note": LOWEST_KEY,
        "high_note": HIGHEST_KEY,
        "low_velocity": SOFTEST_VELOCITY,
        "high_velocity": LOUDEST_VELOCITY,
    }
)


def format_bytes(sample: Sample) -> bytes:
    """The record stating how wide one frame is and how fast the frames go by."""
    block = sample.channels * sample.depth.bytes_per_frame
    return FORMAT_CHUNK.pack(
        {
            "encoding": INTEGER_SAMPLES,
            "channels": sample.channels,
            "rate": sample.rate,
            "byte_rate": sample.rate * block,
            "block_align": block,
            "bits": int(sample.depth),
        }
    )


def frame_bytes(sample: Sample) -> bytes:
    """The waveform as this container stores it: whole amplitudes with the channels interleaved."""
    return encode_pcm(
        np.ascontiguousarray(sample.pcm).reshape(-1),
        depth=sample.depth,
        encoding=STORED_ENCODING,
        sign=STORED_SIGNS[sample.depth],
    )


def loop_bytes(loop: Loop) -> bytes:
    """One loop record, whose end names the last frame the region plays."""
    mode = PING_PONG_LOOP if loop.mode is LoopMode.PING_PONG else FORWARD_LOOP
    return SAMPLER_LOOP.pack(
        {
            "identifier": 0,
            "mode": mode,
            "begin": loop.begin,
            "end": loop.end - 1,
            "fraction": 0,
            "plays": LOOPS_FOREVER,
        }
    )


def loop_records(sample: Sample) -> tuple[bytes, ...]:
    """The loop records a sampler chunk carries, the sustain loop first.

    Order is what tells the two apart, since a record says nothing about which loop it is. A sample
    looping over its sustain alone therefore states a second record spanning nothing, which keeps the
    sustain loop first of a pair rather than reading as the ordinary loop.
    """
    if sample.sustain_loop is None:
        return () if sample.loop is None else (loop_bytes(sample.loop),)

    ordinary = NO_LOOP if sample.loop is None else loop_bytes(sample.loop)
    return (loop_bytes(sample.sustain_loop), ordinary)


def sampler_bytes(sample: Sample) -> bytes:
    """The chunk stating the pitch the waveform sounds unaltered, followed by its loops."""
    records = loop_records(sample)
    header = SAMPLER_CHUNK.pack(
        {
            "manufacturer": 0,
            "product": 0,
            "period": NANOSECONDS // sample.rate,
            "base_note": RATE_NOTE,
            "pitch_fraction": 0,
            "smpte_format": 0,
            "smpte_offset": 0,
            "loops": len(records),
            "sampler_bytes": 0,
        }
    )
    return header + b"".join(records)


def extra_bytes(sample: Sample) -> bytes:
    """The chunk carrying what a tracker's own sample header holds beside the frames.

    The two names follow the record, which is where a tracker reading this container looks for the name
    it shows and the filename it remembers.
    """
    panning = CENTRE_PANNING if sample.panning is None else sample.panning
    flags = NO_FLAGS if sample.panning is None else PANNING_SET
    record = EXTRA_CHUNK.pack(
        {
            "flags": flags,
            "panning": panning,
            "volume": sample.volume * STORED_VOLUME_SCALE,
            "gain": sample.gain,
            "reserved": 0,
            "vibrato_type": STORED_WAVEFORMS.get(sample.vibrato.waveform, DEFAULT_WAVEFORM),
            "vibrato_sweep": sample.vibrato.rate,
            "vibrato_depth": sample.vibrato.depth,
            "vibrato_rate": sample.vibrato.speed,
        }
    )
    return record + encode_name(sample.name, NAME_BYTES) + encode_name(sample.filename, FILENAME_BYTES)


def name_bytes(sample: Sample) -> bytes:
    """The list of information chunks, holding the title every reader of this container knows to look for."""
    return INFO_FORM + tagged(NAME_TAG, encode_text(sample.name))


def write_sample(sample: Sample) -> bytes:
    """Serialize one waveform as a RIFF audio file, carrying how a tracker sounds it.

    Beside the frames the file states the loops, the pitch the waveform sounds unaltered, the level and
    the position it plays at, its auto-vibrato and its two names -- the settings OpenMPT writes into a
    sample it exports, so a file written here opens in a tracker as the sample it came from and any
    audio editor plays it as an ordinary ``.wav``.

    The pitch travels as the rate the frames go by, which is what every reader of this container sounds
    them at. A FastTracker header arrives at its rate through a semitone offset and a finetune trim of
    its own, and those two stay with the module holding them -- the file here names the rate they reach.
    """
    return wrapped(
        tagged(FORMAT_TAG, format_bytes(sample))
        + tagged(DATA_TAG, frame_bytes(sample))
        + tagged(SAMPLER_TAG, sampler_bytes(sample))
        + tagged(INSTRUMENT_TAG, INSTRUMENT_RECORD)
        + tagged(EXTRA_TAG, extra_bytes(sample))
        + tagged(LIST_TAG, name_bytes(sample))
    )


def save_sample(sample: Sample, path: Path) -> None:
    """Serialize one waveform and write it to ``path``."""
    path.write_bytes(write_sample(sample))

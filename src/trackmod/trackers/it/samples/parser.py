from typing import Final

import numpy as np
from numpy.typing import NDArray

from trackmod.binary.pcm.codec import decode_pcm
from trackmod.binary.pcm.quantise import dequantise
from trackmod.binary.records.values import RecordValues, read_bytes, read_int
from trackmod.binary.text import decode_name
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.sample import STEREO_CHANNELS, Sample
from trackmod.core.samples.vibrato import Vibrato
from trackmod.trackers.it.layout.sample import SAMPLE_HEADER
from trackmod.trackers.it.panning import shared_panning
from trackmod.trackers.it.samples.compression import compressed_bytes, decompress
from trackmod.trackers.it.spec.flags import SampleFlag, SamplePanning
from trackmod.trackers.it.spec.storage import PCM_ENCODING

MONO_CHANNELS: Final = 1


def stored_depth(values: RecordValues) -> BitDepth:
    """The bit depth a sample header's flags declare its frames are stored at."""
    return BitDepth.SIXTEEN if SampleFlag(read_int(values, "flags")) & SampleFlag.SIXTEEN_BIT else BitDepth.EIGHT


def stored_channels(values: RecordValues) -> int:
    """How many channels a sample header's flags declare its frames are stored as."""
    return STEREO_CHANNELS if SampleFlag(read_int(values, "flags")) & SampleFlag.STEREO else MONO_CHANNELS


def is_compressed(values: RecordValues) -> bool:
    """Whether a sample header states its waveform is stored in compressed blocks."""
    return SampleFlag.COMPRESSED in SampleFlag(read_int(values, "flags"))


def stored_frames(values: RecordValues) -> int:
    """How many bytes of waveform a sample header points at, across every channel it stores.

    A compressed waveform states its own length block by block, so a reader is given the rest of the file
    and stops once the frame count the header names is out.
    """
    return read_int(values, "length") * stored_depth(values).bytes_per_frame * stored_channels(values)


def _compressed_extents(data: bytes, *, frames: int, depth: BitDepth, channels: int) -> tuple[int, ...]:
    """How many bytes each channel of a compressed waveform occupies, one entry per channel.

    A stereo waveform stores two independent streams, the left channel's blocks in full before the right
    channel's own fresh sequence begins, so the right channel's extent is measured from where the left
    one ended.
    """
    left = compressed_bytes(data, frames=frames, depth=depth)
    if channels == MONO_CHANNELS:
        return (left,)

    right = compressed_bytes(data[left:], frames=frames, depth=depth)
    return left, right


def stored_end(values: RecordValues, data: bytes) -> int:
    """The byte past the frames a sample header points at, which a compressed block states for itself."""
    start = read_int(values, "sample_pointer")
    if not is_compressed(values):
        return start + stored_frames(values)

    extents = _compressed_extents(
        data[start:], frames=read_int(values, "length"), depth=stored_depth(values), channels=stored_channels(values)
    )
    return start + sum(extents)


def loop_mode(flags: SampleFlag, ping_pong: SampleFlag) -> LoopMode:
    """Which direction a loop runs, given the flag that marks it as bidirectional."""
    return LoopMode.PING_PONG if ping_pong in flags else LoopMode.FORWARD


def read_loop(values: RecordValues, *, begin: str, end: str, mode: LoopMode) -> Loop | None:
    """One loop read from its pair of frame-index fields, or ``None`` when the range is empty."""
    first, last = read_int(values, begin), read_int(values, end)
    if last <= first:
        return None

    return Loop(begin=first, end=last, mode=mode)


def stored_pcm(values: RecordValues, data: bytes, *, depth: BitDepth, doubled: bool) -> NDArray[np.float64]:
    """The waveform a sample header points at, however its frames and channels are stored."""
    length = read_int(values, "length")
    if stored_channels(values) == MONO_CHANNELS:
        if is_compressed(values):
            frames = decompress(data, frames=length, depth=depth, doubled=doubled)
            return dequantise(frames, depth)

        return decode_pcm(data, depth=depth, encoding=PCM_ENCODING)

    if is_compressed(values):
        left_bytes, _ = _compressed_extents(data, frames=length, depth=depth, channels=STEREO_CHANNELS)
        left = decompress(data, frames=length, depth=depth, doubled=doubled)
        right = decompress(data[left_bytes:], frames=length, depth=depth, doubled=doubled)
        return dequantise(np.stack([left, right], axis=1), depth)

    mono_bytes = length * depth.bytes_per_frame
    left_pcm = decode_pcm(data[:mono_bytes], depth=depth, encoding=PCM_ENCODING)
    right_pcm = decode_pcm(data[mono_bytes:], depth=depth, encoding=PCM_ENCODING)
    return np.stack([left_pcm, right_pcm], axis=1)


def parse_sample(values: RecordValues, data: bytes, *, doubled: bool) -> Sample:
    """Rebuild a sample from its header fields and the frames the header points at."""
    flags = SampleFlag(read_int(values, "flags"))
    depth = stored_depth(values)
    panning = read_int(values, "default_pan")
    loop = (
        read_loop(values, begin="loop_begin", end="loop_end", mode=loop_mode(flags, SampleFlag.PING_PONG_LOOP))
        if SampleFlag.LOOP in flags
        else None
    )
    sustain = (
        read_loop(
            values,
            begin="sustain_begin",
            end="sustain_end",
            mode=loop_mode(flags, SampleFlag.PING_PONG_SUSTAIN),
        )
        if SampleFlag.SUSTAIN_LOOP in flags
        else None
    )
    return Sample(
        name=decode_name(read_bytes(values, "name")),
        pcm=stored_pcm(values, data, depth=depth, doubled=doubled),
        rate=read_int(values, "c5speed"),
        depth=depth,
        volume=read_int(values, "default_volume"),
        gain=read_int(values, "global_volume"),
        panning=shared_panning(panning & ~SamplePanning.ENABLED) if panning & SamplePanning.ENABLED else None,
        loop=loop,
        sustain_loop=sustain,
        filename=decode_name(read_bytes(values, "filename")),
        vibrato=Vibrato(
            speed=read_int(values, "vibrato_speed"),
            depth=read_int(values, "vibrato_depth"),
            rate=read_int(values, "vibrato_rate"),
            waveform=read_int(values, "vibrato_waveform"),
        ),
    )


def read_sample(data: bytes, *, offset: int, doubled: bool) -> Sample:
    """The sample whose header sits at ``offset``, with the frames the header points at.

    Both containers this format writes find a waveform the same way — through a pointer counted from the
    start of the file — so the header's position is all a reader needs to be told.
    """
    values = SAMPLE_HEADER.unpack(data[offset:])
    start = read_int(values, "sample_pointer")
    if is_compressed(values):
        return parse_sample(values, data[start:], doubled=doubled)

    return parse_sample(values, data[start : start + stored_frames(values)], doubled=doubled)

from collections.abc import Mapping
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from trackmod.binary.pcm.codec import decode_pcm
from trackmod.binary.records.values import read_int
from trackmod.binary.text import decode_name, decode_text
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.sample import MONO_CHANNELS, STEREO_CHANNELS, Sample
from trackmod.core.samples.vibrato import Vibrato
from trackmod.spec.levels import MAX_PANNING, MAX_VOLUME
from trackmod.wave.chunks import formed, required, unwrapped
from trackmod.wave.layout import EXTRA_CHUNK, FORMAT_CHUNK, SAMPLER_CHUNK, SAMPLER_LOOP
from trackmod.wave.settings import WaveSettings
from trackmod.wave.spec import (
    DATA_TAG,
    DEFAULT_WAVEFORM,
    EXTRA_CHUNK_BYTES,
    EXTRA_TAG,
    FILENAME_BYTES,
    FORMAT_CHUNK_BYTES,
    FORMAT_TAG,
    INFO_FORM,
    INTEGER_SAMPLES,
    LIST_TAG,
    MAX_LOOPS,
    NAME_BYTES,
    NAME_TAG,
    PANNING_SET,
    PING_PONG_LOOP,
    SAMPLER_CHUNK_BYTES,
    SAMPLER_LOOP_BYTES,
    SAMPLER_TAG,
    SHARED_WAVEFORMS,
    STORED_ENCODING,
    STORED_SIGNS,
    STORED_VOLUME_SCALE,
    SUSTAIN_LOOPS,
)

CHANNEL_COUNTS = (MONO_CHANNELS, STEREO_CHANNELS)
DEPTHS = tuple(int(depth) for depth in BitDepth)


def wave_format(payload: bytes) -> tuple[int, int, BitDepth]:
    """How many channels the waveform carries, the rate it sounds at, and how wide one stored frame is.

    Raises:
        ValueError: when the chunk stops inside the record, or states an encoding other than whole
            amplitudes, a channel count past stereo, or a frame width this library stores.
    """
    if len(payload) < FORMAT_CHUNK_BYTES:
        raise ValueError(f"a format chunk needs {FORMAT_CHUNK_BYTES} bytes, the file states {len(payload)}")

    values = FORMAT_CHUNK.unpack(payload[:FORMAT_CHUNK_BYTES])
    encoding = read_int(values, "encoding")
    if encoding != INTEGER_SAMPLES:
        raise ValueError(f"encoding {encoding} holds something other than whole amplitudes")

    channels = read_int(values, "channels")
    if channels not in CHANNEL_COUNTS:
        raise ValueError(f"{channels} channels, mono and stereo waveforms are the ones read here")

    bits = read_int(values, "bits")
    if bits not in DEPTHS:
        raise ValueError(f"{bits}-bit frames, {' and '.join(str(depth) for depth in DEPTHS)}-bit are read here")

    return channels, read_int(values, "rate"), BitDepth(bits)


def wave_frames(payload: bytes, *, channels: int, depth: BitDepth) -> NDArray[np.float64]:
    """The stored frames as float amplitudes, one column per channel where the waveform is stereo.

    A chunk stopping partway through a frame is read up to the last whole one, which is the part a
    player sounds.
    """
    block = channels * depth.bytes_per_frame
    whole = payload[: len(payload) // block * block]
    pcm = decode_pcm(whole, depth=depth, encoding=STORED_ENCODING, sign=STORED_SIGNS[depth])
    return pcm if channels == MONO_CHANNELS else pcm.reshape(-1, channels)


def stored_loop(payload: bytes, index: int, *, frames: int) -> Loop | None:
    """One stored loop as a frame range, ``None`` where the record spans nothing.

    A stored end names the last frame the region plays, so the half-open range this returns reaches one
    frame further.
    """
    values = SAMPLER_LOOP.unpack_at(payload, SAMPLER_CHUNK_BYTES + index * SAMPLER_LOOP_BYTES)
    last = read_int(values, "end")
    if last == 0:
        return None

    begin = min(read_int(values, "begin"), frames)
    end = min(max(last, begin), frames)
    if end < frames:
        end += 1

    if end <= begin:
        return None

    mode = LoopMode.PING_PONG if read_int(values, "mode") == PING_PONG_LOOP else LoopMode.FORWARD
    return Loop(begin=begin, end=end, mode=mode)


def stored_loops(payload: bytes, *, frames: int) -> tuple[Loop | None, Loop | None]:
    """The sustain loop and the ordinary loop a sampler chunk states, in that order.

    A chunk holding one record states the ordinary loop; a chunk holding two states the sustain loop
    first, which is the order a writer of this container lays them in.
    """
    if len(payload) < SAMPLER_CHUNK_BYTES:
        return (None, None)

    values = SAMPLER_CHUNK.unpack(payload[:SAMPLER_CHUNK_BYTES])
    count = min(read_int(values, "loops"), MAX_LOOPS)
    held = tuple(stored_loop(payload, index, frames=frames) for index in range(count))
    if count >= SUSTAIN_LOOPS:
        return (held[0], held[1])

    return (None, held[0] if held else None)


def stored_settings(payload: bytes) -> WaveSettings:
    """How a tracker sounds the waveform, as the extra chunk states it.

    A file carrying no such chunk sounds at the defaults :class:`WaveSettings` holds.
    """
    if len(payload) < EXTRA_CHUNK_BYTES:
        return WaveSettings()

    values = EXTRA_CHUNK.unpack(payload[:EXTRA_CHUNK_BYTES])
    placed = bool(read_int(values, "flags") & PANNING_SET)
    names = payload[EXTRA_CHUNK_BYTES:]
    return WaveSettings(
        volume=min(read_int(values, "volume") // STORED_VOLUME_SCALE, MAX_VOLUME),
        gain=min(read_int(values, "gain"), MAX_VOLUME),
        panning=min(read_int(values, "panning"), MAX_PANNING) if placed else None,
        vibrato=Vibrato(
            speed=read_int(values, "vibrato_rate"),
            depth=read_int(values, "vibrato_depth"),
            rate=read_int(values, "vibrato_sweep"),
            waveform=SHARED_WAVEFORMS.get(read_int(values, "vibrato_type"), DEFAULT_WAVEFORM),
        ),
        name=decode_name(names[:NAME_BYTES]),
        filename=decode_name(names[NAME_BYTES : NAME_BYTES + FILENAME_BYTES]),
    )


def stored_name(held: Mapping[bytes, bytes], fallback: str) -> str:
    """The title a file's list of information chunks states, falling back on what a tracker wrote."""
    information = formed(held.get(LIST_TAG, b""), INFO_FORM)
    title = information.get(NAME_TAG)
    return fallback if title is None else decode_text(title)


def parse_sample(data: bytes) -> Sample:
    """Read a RIFF audio file back as the sample it states.

    The frames, their rate and their width come from the file itself, and everything a tracker sounds
    them with -- the loops, the level, the position, the auto-vibrato and the two names -- comes from
    the chunks a tracker adds. An ordinary ``.wav`` from anywhere else carries the frames alone and
    arrives at full level with no loop, which is how a player sounds it.

    Raises:
        ValueError: when the bytes state something other than a RIFF file of WAVE chunks, or hold
            neither a format chunk nor frames.
    """
    held = unwrapped(data)
    channels, rate, depth = wave_format(required(held, FORMAT_TAG))
    pcm = wave_frames(required(held, DATA_TAG), channels=channels, depth=depth)
    sustain_loop, loop = stored_loops(held.get(SAMPLER_TAG, b""), frames=int(pcm.shape[0]))
    settings = stored_settings(held.get(EXTRA_TAG, b""))
    return Sample(
        name=stored_name(held, settings.name),
        filename=settings.filename,
        pcm=pcm,
        rate=rate,
        depth=depth,
        volume=settings.volume,
        gain=settings.gain,
        panning=settings.panning,
        vibrato=settings.vibrato,
        loop=loop,
        sustain_loop=sustain_loop,
    )


def load_sample(path: Path) -> Sample:
    """Read a RIFF audio file from ``path`` as the sample it states."""
    return parse_sample(path.read_bytes())

from trackmod.binary.pcm.codec import encode_pcm
from trackmod.binary.text import encode_name
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.sample import STEREO_CHANNELS, Sample
from trackmod.trackers.it.layout.sample import SAMPLE_HEADER
from trackmod.trackers.it.panning import stored_panning
from trackmod.trackers.it.spec.flags import SampleConvert, SampleFlag, SamplePanning
from trackmod.trackers.it.spec.identity import MAGIC_SAMPLE
from trackmod.trackers.it.spec.sizes import FILENAME_BYTES, NAME_BYTES
from trackmod.trackers.it.spec.storage import PCM_ENCODING, PCM_SIGN


def sample_bytes(sample: Sample) -> bytes:
    """Serialise a sample's waveform as this format stores it: signed frames, no differencing.

    A stereo waveform is stored planar, so each channel is encoded from its own 1-D slice and the two
    are placed one after the other, which is the order a reader of this format walks them in.
    """
    if sample.channels != STEREO_CHANNELS:
        return encode_pcm(sample.pcm, depth=sample.depth, encoding=PCM_ENCODING, sign=PCM_SIGN)

    left = encode_pcm(sample.pcm[:, 0], depth=sample.depth, encoding=PCM_ENCODING, sign=PCM_SIGN)
    right = encode_pcm(sample.pcm[:, 1], depth=sample.depth, encoding=PCM_ENCODING, sign=PCM_SIGN)
    return left + right


def loop_flags(sample: Sample) -> SampleFlag:
    """The looping switches a sample's two loops set in its header."""
    flags = SampleFlag(0)
    if sample.loop is not None:
        flags |= SampleFlag.LOOP
        if sample.loop.mode is LoopMode.PING_PONG:
            flags |= SampleFlag.PING_PONG_LOOP

    if sample.sustain_loop is not None:
        flags |= SampleFlag.SUSTAIN_LOOP
        if sample.sustain_loop.mode is LoopMode.PING_PONG:
            flags |= SampleFlag.PING_PONG_SUSTAIN

    return flags


def loop_bounds(loop: Loop | None) -> tuple[int, int]:
    """The frame range a loop stores, which is empty when the sample carries no loop."""
    return (0, 0) if loop is None else (loop.begin, loop.end)


def sample_header(sample: Sample, *, data_offset: int) -> bytes:
    """Serialise a sample header pointing at where its frames sit in the file."""
    flags = SampleFlag.DATA | loop_flags(sample)
    if sample.depth is BitDepth.SIXTEEN:
        flags |= SampleFlag.SIXTEEN_BIT

    if sample.channels == STEREO_CHANNELS:
        flags |= SampleFlag.STEREO

    loop_begin, loop_end = loop_bounds(sample.loop)
    sustain_begin, sustain_end = loop_bounds(sample.sustain_loop)
    panning = 0 if sample.panning is None else SamplePanning.ENABLED | stored_panning(sample.panning)
    return SAMPLE_HEADER.pack(
        {
            "magic": MAGIC_SAMPLE,
            "filename": encode_name(sample.filename, FILENAME_BYTES),
            "global_volume": sample.gain,
            "flags": int(flags),
            "default_volume": sample.volume,
            "name": encode_name(sample.name, NAME_BYTES),
            "convert": int(SampleConvert.SIGNED),
            "default_pan": panning,
            "length": sample.frames,
            "loop_begin": loop_begin,
            "loop_end": loop_end,
            "c5speed": sample.rate,
            "sustain_begin": sustain_begin,
            "sustain_end": sustain_end,
            "sample_pointer": data_offset,
            "vibrato_speed": sample.vibrato.speed,
            "vibrato_depth": sample.vibrato.depth,
            "vibrato_rate": sample.vibrato.rate,
            "vibrato_waveform": sample.vibrato.waveform,
        }
    )

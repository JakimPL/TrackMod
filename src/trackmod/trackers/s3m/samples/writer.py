from typing import Final

from trackmod.binary.pcm.codec import encode_pcm
from trackmod.binary.text import encode_name
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.loop import LoopMode
from trackmod.core.samples.sample import STEREO_CHANNELS, Sample
from trackmod.trackers.s3m.layout.instrument import INSTRUMENT_RECORD
from trackmod.trackers.s3m.parapointers import split_pointer
from trackmod.trackers.s3m.spec.defaults import NO_FRAMES, NO_LOOP
from trackmod.trackers.s3m.spec.flags import RecordType, SampleFlag
from trackmod.trackers.s3m.spec.identity import MAGIC_SAMPLE
from trackmod.trackers.s3m.spec.sizes import FILENAME_BYTES, NAME_BYTES
from trackmod.trackers.s3m.spec.storage import PCM_ENCODING, PCM_SIGN, UNPACKED

NO_POINTER: Final = 0


def reject_unstorable(sample: Sample) -> None:
    """Refuse to serialise a sample this format keeps no field for.

    Raises:
        ValueError: when the sample is panned, carries a sustain loop, or loops in a direction other
            than forwards -- none of which an instrument record here has room to state.
    """
    if sample.panning is not None:
        raise ValueError(f"sample {sample.name!r} carries a panning, and this format pans by channel")

    if sample.sustain_loop is not None:
        raise ValueError(f"sample {sample.name!r} carries a sustain loop, which this format cannot store")

    if sample.loop is not None and sample.loop.mode is not LoopMode.FORWARD:
        raise ValueError(f"sample {sample.name!r} loops {sample.loop.mode}, and this format loops forwards")


def sample_bytes(sample: Sample) -> bytes:
    """Serialise a waveform as this format stores it: frames shifted into the positive half of their range.

    A stereo waveform is stored a channel at a time, the left in full before the right, so each is
    encoded from its own slice.
    """
    reject_unstorable(sample)
    if sample.channels != STEREO_CHANNELS:
        return encode_pcm(sample.pcm, depth=sample.depth, encoding=PCM_ENCODING, sign=PCM_SIGN)

    left = encode_pcm(sample.pcm[:, 0], depth=sample.depth, encoding=PCM_ENCODING, sign=PCM_SIGN)
    right = encode_pcm(sample.pcm[:, 1], depth=sample.depth, encoding=PCM_ENCODING, sign=PCM_SIGN)
    return left + right


def sample_flags(sample: Sample) -> SampleFlag:
    """The storage and looping switches a sample sets in its record."""
    flags = SampleFlag(0)
    if sample.loop is not None:
        flags |= SampleFlag.LOOP

    if sample.channels == STEREO_CHANNELS:
        flags |= SampleFlag.STEREO

    if sample.depth is BitDepth.SIXTEEN:
        flags |= SampleFlag.SIXTEEN_BIT

    return flags


def sample_record(sample: Sample, *, data_offset: int) -> bytes:
    """Serialise an instrument record pointing at the paragraph its frames begin on.

    A slot holding no frames states so in the byte it opens with, which keeps the numbering the cells
    count on while the file spends nothing on a waveform.
    """
    reject_unstorable(sample)
    loop = sample.loop
    sounding = sample.frames > NO_FRAMES
    high, low = split_pointer(data_offset) if sounding else (NO_POINTER, NO_POINTER)
    return INSTRUMENT_RECORD.pack(
        {
            "type": int(RecordType.SAMPLE if sounding else RecordType.EMPTY),
            "filename": encode_name(sample.filename, FILENAME_BYTES),
            "frames_high": high,
            "frames_low": low,
            "length": sample.frames,
            "loop_begin": NO_LOOP if loop is None else loop.begin,
            "loop_end": NO_LOOP if loop is None else loop.end,
            "volume": sample.volume,
            "pack": UNPACKED,
            "flags": int(sample_flags(sample)),
            "c2spd": sample.rate,
            "name": encode_name(sample.name, NAME_BYTES),
            "magic": MAGIC_SAMPLE,
        }
    )

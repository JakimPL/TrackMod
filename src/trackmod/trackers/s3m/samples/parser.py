from typing import Final

import numpy as np
from numpy.typing import NDArray

from trackmod.binary.pcm.blocks import paired_channels, whole_frames
from trackmod.binary.pcm.codec import decode_pcm
from trackmod.binary.pcm.sign import PcmSign
from trackmod.binary.records.values import RecordValues, read_bytes, read_int
from trackmod.binary.text import decode_name
from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.repair import repaired_loop, repaired_rate, repaired_waveform
from trackmod.core.samples.sample import STEREO_CHANNELS, Sample
from trackmod.spec.levels import MAX_VOLUME
from trackmod.trackers.s3m.parapointers import joined_pointer
from trackmod.trackers.s3m.spec.defaults import NO_FRAMES
from trackmod.trackers.s3m.spec.flags import RecordType, SampleFlag
from trackmod.trackers.s3m.spec.identity import SIGNED_FRAMES
from trackmod.trackers.s3m.spec.storage import PCM_ENCODING, PCM_SIGN, UNPACKED

MONO_CHANNELS: Final = 1


def record_type(values: RecordValues, *, subject: str) -> RecordType:
    """What one instrument record holds, as the byte it opens with states it.

    Raises:
        ValueError: when the byte names none of the kinds this format defines.
    """
    stated = read_int(values, "type")
    if stated not in RecordType:
        raise ValueError(f"{subject} opens with {stated}, which names none of the records this format defines")

    return RecordType(stated)


def frame_sign(frame_format: int) -> PcmSign:
    """Which half of the stored range a module's waveforms sit in, as its header states it.

    Scream Tracker 3 wrote signed frames in its first release and unsigned ones in every release after,
    and states which in the header, so a reader follows the header rather than the release.
    """
    return PcmSign.SIGNED if frame_format == SIGNED_FRAMES else PCM_SIGN


def stored_depth(values: RecordValues) -> BitDepth:
    """The bit depth a record's flags declare its frames are stored at."""
    return BitDepth.SIXTEEN if SampleFlag(read_int(values, "flags")) & SampleFlag.SIXTEEN_BIT else BitDepth.EIGHT


def stored_channels(values: RecordValues) -> int:
    """How many channels a record's flags declare its frames are stored as."""
    return STEREO_CHANNELS if SampleFlag(read_int(values, "flags")) & SampleFlag.STEREO else MONO_CHANNELS


def stored_bytes(values: RecordValues) -> int:
    """How many bytes of waveform a record points at, across every channel it stores."""
    return read_int(values, "length") * stored_depth(values).bytes_per_frame * stored_channels(values)


def waveform_start(values: RecordValues) -> int:
    """Where the frames a record points at begin, which its three pointer bytes name a paragraph of."""
    return joined_pointer(read_int(values, "frames_high"), read_int(values, "frames_low"))


def reject_packed(values: RecordValues, *, subject: str) -> None:
    """Refuse a record whose frames are stored in a packing this reader sounds no part of.

    Raises:
        ValueError: when the record states a packing, which is the ADPCM a later tracker wrote.
    """
    packing = read_int(values, "pack")
    if packing != UNPACKED:
        raise ValueError(f"{subject} states packing {packing}, and this reader holds unpacked frames")


def reject_adlib(values: RecordValues, *, subject: str) -> None:
    """Refuse a record describing an OPL patch rather than a waveform.

    Raises:
        ValueError: when the record names one of the synthesiser kinds, which carry registers in place
            of frames.
    """
    kind = record_type(values, subject=subject)
    if kind not in (RecordType.EMPTY, RecordType.SAMPLE):
        raise ValueError(f"{subject} is {kind.name.lower()}, an OPL patch stated as registers rather than frames")


def read_loop(values: RecordValues, *, subject: str, repairs: Repairs) -> Loop | None:
    """The loop a record declares, or ``None`` when the waveform plays through once.

    A record can raise the loop flag over a pair of points that meet, which repeats nothing at all, so
    the waveform plays through once and the claim the flag made is reported.
    """
    if not SampleFlag(read_int(values, "flags")) & SampleFlag.LOOP:
        return None

    begin, end = read_int(values, "loop_begin"), read_int(values, "loop_end")
    if end > begin:
        return Loop(begin=begin, end=end, mode=LoopMode.FORWARD)

    repairs.made(f"loop {begin}..{end} spans no frame and reads as none", subject=subject)
    return None


def stored_pcm(values: RecordValues, data: bytes, *, depth: BitDepth, sign: PcmSign) -> NDArray[np.float64]:
    """The waveform a record points at, however many channels it stores.

    A stereo waveform holds each channel's frames in full, the left before the right, so the two are
    read from their own halves of the block rather than out of one interleaved run. Each half is read
    as far as whole frames go and the pair as far as both halves reach, so a block the file stops
    inside sounds the frames it holds.
    """
    if stored_channels(values) == MONO_CHANNELS:
        return decode_pcm(whole_frames(data, depth=depth), depth=depth, encoding=PCM_ENCODING, sign=sign)

    left, right = paired_channels(data, block=read_int(values, "length") * depth.bytes_per_frame, depth=depth)
    return np.stack(
        [
            decode_pcm(left, depth=depth, encoding=PCM_ENCODING, sign=sign),
            decode_pcm(right, depth=depth, encoding=PCM_ENCODING, sign=sign),
        ],
        axis=1,
    )


def read_volume(values: RecordValues, *, subject: str, repairs: Repairs) -> int:
    """The level a record states, drawn back to full where a file states more than full."""
    volume = read_int(values, "volume")
    if volume <= MAX_VOLUME:
        return volume

    repairs.made(f"volume {volume} read as {MAX_VOLUME}", subject=subject)
    return MAX_VOLUME


def empty_slot(values: RecordValues, *, subject: str, repairs: Repairs) -> Sample:
    """The placeholder a record holding no waveform reads as, which keeps a song's numbering in place.

    A slot standing empty still carries the name, the rate, the level and the width a tracker held ready
    for the waveform to come, so all of them are kept and a module written again states what it stated.
    """
    return Sample(
        name=decode_name(read_bytes(values, "name")),
        pcm=np.zeros(NO_FRAMES),
        rate=repaired_rate(read_int(values, "c2spd"), subject=subject, repairs=repairs),
        depth=stored_depth(values),
        volume=read_volume(values, subject=subject, repairs=repairs),
        filename=decode_name(read_bytes(values, "filename")),
    )


def parse_sample(
    values: RecordValues,
    data: bytes,
    *,
    sign: PcmSign,
    subject: str,
    repairs: Repairs,
) -> Sample:
    """Rebuild a sample from its record and the frames the record points at.

    A loop stated past the frames that were stored, a loop spanning no frame, a rate of zero and a
    waveform the file holds a part of are drawn into range and recorded in ``repairs``.

    Raises:
        ValueError: when the record describes an OPL patch or states a packing.
    """
    reject_adlib(values, subject=subject)
    if record_type(values, subject=subject) is RecordType.EMPTY:
        return empty_slot(values, subject=subject, repairs=repairs)

    reject_packed(values, subject=subject)
    depth = stored_depth(values)
    pcm = repaired_waveform(
        stored_pcm(values, data, depth=depth, sign=sign),
        stated=read_int(values, "length"),
        subject=subject,
        repairs=repairs,
    )
    return Sample(
        name=decode_name(read_bytes(values, "name")),
        pcm=pcm,
        rate=repaired_rate(read_int(values, "c2spd"), subject=subject, repairs=repairs),
        depth=depth,
        volume=read_volume(values, subject=subject, repairs=repairs),
        loop=repaired_loop(
            read_loop(values, subject=subject, repairs=repairs),
            frames=int(pcm.shape[0]),
            name="loop",
            subject=subject,
            repairs=repairs,
        ),
        filename=decode_name(read_bytes(values, "filename")),
    )


def stated_frames(values: RecordValues, data: bytes) -> bytes:
    """The block of frames a record points at, as far as the file goes on to hold it."""
    start = waveform_start(values)
    return data[start : start + stored_bytes(values)]

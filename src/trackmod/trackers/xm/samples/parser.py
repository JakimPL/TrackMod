from typing import Final

from trackmod.binary.cursor import Cursor
from trackmod.binary.pcm.codec import decode_pcm
from trackmod.binary.records.values import RecordValues, read_bytes, read_int
from trackmod.binary.text import decode_name
from trackmod.core.notes.pitch import Note
from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.repair import repaired_loop
from trackmod.core.samples.sample import Sample
from trackmod.spec.pitch import RATE_NOTE
from trackmod.trackers.xm.layout.sample import SAMPLE_HEADER
from trackmod.trackers.xm.spec.flags import LOOP_TYPE_MASK, LoopType, SampleFlag
from trackmod.trackers.xm.spec.sizes import SAMPLE_HEADER_BYTES
from trackmod.trackers.xm.spec.storage import PCM_ENCODING, PCM_SIGN
from trackmod.trackers.xm.tuning import Tuning, tuned_rate

LOOP_MODES: Final[dict[int, LoopMode]] = {
    LoopType.FORWARD: LoopMode.FORWARD,
    LoopType.PING_PONG: LoopMode.PING_PONG,
}


def stored_depth(values: RecordValues) -> BitDepth:
    """The bit depth a sample header's type byte declares its frames are stored at."""
    return BitDepth.SIXTEEN if read_int(values, "type") & SampleFlag.SIXTEEN_BIT else BitDepth.EIGHT


def stored_bytes(values: RecordValues) -> int:
    """How many bytes of waveform follow a sample header, which is what its length field counts."""
    return read_int(values, "length")


def stored_tuning(values: RecordValues) -> Tuning:
    """The transposition a sample header states."""
    return Tuning(
        relative_note=read_int(values, "relative_note"),
        finetune=read_int(values, "finetune"),
    )


def read_loop(values: RecordValues, *, stride: int) -> Loop | None:
    """The loop a sample header declares, counted back into frames, or ``None`` when it runs no loop."""
    mode = LOOP_MODES.get(read_int(values, "type") & LOOP_TYPE_MASK)
    length = read_int(values, "loop_length") // stride
    if mode is None or length == 0:
        return None

    begin = read_int(values, "loop_begin") // stride
    return Loop(begin=begin, end=begin + length, mode=mode)


def parse_sample(values: RecordValues, data: bytes, *, subject: str, repairs: Repairs) -> Sample:
    """Rebuild a sample from its header fields and the frames that follow it.

    A stored sample states no rate, only how far it is transposed from the key that plays it, so the
    rate is read back at the key the shared model states a rate against. The transposition itself is
    also carried onto the sample as read, so a caller can see the header's own bytes rather than only
    the rate they were derived into.
    """
    depth = stored_depth(values)
    reference = Note(RATE_NOTE)
    tuning = stored_tuning(values)
    pcm = decode_pcm(data, depth=depth, encoding=PCM_ENCODING, sign=PCM_SIGN)
    loop = read_loop(values, stride=depth.bytes_per_frame)
    return Sample(
        name=decode_name(read_bytes(values, "name")),
        pcm=pcm,
        rate=tuned_rate(tuning, key=reference, sounded=reference),
        depth=depth,
        volume=read_int(values, "volume"),
        panning=read_int(values, "panning"),
        loop=repaired_loop(loop, frames=int(pcm.shape[0]), name="loop", subject=subject, repairs=repairs),
        relative_note=tuning.relative_note,
        finetune=tuning.finetune,
    )


def stated_frames(cursor: Cursor, values: RecordValues, *, subject: str, repairs: Repairs) -> bytes:
    """The waveform following a sample header, as far as the file goes on to hold it.

    A header states how many bytes of frames follow it, and files state more than they carry -- most
    often where a module was truncated in transit. The frames that are there are the ones that sound.
    """
    stated = stored_bytes(values)
    if stated <= cursor.remaining:
        return cursor.take(stated)

    stride = stored_depth(values).bytes_per_frame
    held = (cursor.remaining // stride) * stride
    repairs.made(f"waveform of {stated} bytes read as the {held} the file holds", subject=subject)
    frames = cursor.take(held)
    cursor.take_at_most(stated - held)
    return frames


def read_samples(cursor: Cursor, *, count: int, subject: str, repairs: Repairs) -> tuple[Sample, ...]:
    """The samples one instrument owns: every header first, then every waveform, as they are laid out.

    Both containers this format writes store an instrument's samples this way, so a reader that has
    reached the end of an instrument header continues here whichever file it is walking.
    """
    headers: list[RecordValues] = []
    for _ in range(count):
        headers.append(SAMPLE_HEADER.unpack(cursor.peek_padded(SAMPLE_HEADER_BYTES)))
        cursor.take_at_most(SAMPLE_HEADER_BYTES)

    return tuple(
        parse_sample(
            values,
            stated_frames(cursor, values, subject=f"{subject} sample {index}", repairs=repairs),
            subject=f"{subject} sample {index}",
            repairs=repairs,
        )
        for index, values in enumerate(headers)
    )

from trackmod.binary.cursor import Cursor
from trackmod.binary.pcm.codec import decode_pcm
from trackmod.binary.records.values import RecordValues, read_bytes, read_int
from trackmod.binary.text import decode_name
from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.repair import repaired_loop
from trackmod.core.samples.sample import Sample
from trackmod.spec.levels import MAX_VOLUME
from trackmod.spec.width import NIBBLE_MAX
from trackmod.trackers.amiga.spec.defaults import NO_LOOP_LENGTH
from trackmod.trackers.amiga.spec.sizes import WORD_BYTES
from trackmod.trackers.amiga.spec.storage import PCM_DEPTH, PCM_ENCODING, PCM_SIGN
from trackmod.trackers.amiga.tuning import finetune_rate


def stored_bytes(values: RecordValues) -> int:
    """How many bytes of waveform a sample record states, whose own field counts them in words."""
    return read_int(values, "length") * WORD_BYTES


def read_loop(values: RecordValues, *, begin_unit: int) -> Loop | None:
    """The loop a sample record declares, counted back into frames, or ``None`` when it runs no loop.

    A length counts words, and a length of one word is what a record writes to say a sample plays through
    once, so a loop runs from two words up. The beginning counts in the unit its own format states it in:
    the first trackers of this lineage wrote a byte offset there and the ones after them wrote a word.
    """
    length = read_int(values, "loop_length")
    if length <= NO_LOOP_LENGTH:
        return None

    begin = read_int(values, "loop_begin") * begin_unit
    return Loop(begin=begin, end=begin + length * WORD_BYTES, mode=LoopMode.FORWARD)


def read_volume(values: RecordValues, *, subject: str, repairs: Repairs) -> int:
    """The level a sample record states, drawn back to full where a file states more than full."""
    volume = read_int(values, "volume")
    if volume <= MAX_VOLUME:
        return volume

    repairs.made(f"volume {volume} read as {MAX_VOLUME}", subject=subject)
    return MAX_VOLUME


def parse_sample(values: RecordValues, data: bytes, *, begin_unit: int, subject: str, repairs: Repairs) -> Sample:
    """Rebuild a sample from its record and the frames the file holds for it.

    A record states no rate, only which of the sixteen tuning rows it plays on, so the rate is read back
    from the row. Every waveform here is one channel of eight-bit frames stored as they sound.
    """
    pcm = decode_pcm(data, depth=PCM_DEPTH, encoding=PCM_ENCODING, sign=PCM_SIGN)
    loop = read_loop(values, begin_unit=begin_unit)
    return Sample(
        name=decode_name(read_bytes(values, "name")),
        pcm=pcm,
        rate=finetune_rate(read_int(values, "finetune") & NIBBLE_MAX),
        depth=PCM_DEPTH,
        volume=read_volume(values, subject=subject, repairs=repairs),
        loop=repaired_loop(loop, frames=int(pcm.shape[0]), name="loop", subject=subject, repairs=repairs),
    )


def stated_frames(cursor: Cursor, values: RecordValues, *, subject: str, repairs: Repairs) -> bytes:
    """The waveform a sample record states, as far as the file goes on to hold it."""
    stated = stored_bytes(values)
    if stated <= cursor.remaining:
        return cursor.take(stated)

    held = cursor.remaining
    repairs.made(f"waveform of {stated} bytes read as the {held} the file holds", subject=subject)
    return cursor.take(held)

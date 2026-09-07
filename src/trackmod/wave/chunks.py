from collections.abc import Mapping

from trackmod.binary.cursor import Cursor
from trackmod.binary.records.values import read_bytes, read_int
from trackmod.spec.text import PADDING
from trackmod.wave.layout import CHUNK_HEADER
from trackmod.wave.spec import (
    ALIGNMENT,
    CHUNK_HEADER_BYTES,
    FORM_BYTES,
    RIFF_MAGIC,
    WAVE_FORM,
)


def tagged(tag: bytes, payload: bytes) -> bytes:
    """One chunk as a RIFF file holds it: its tag, its length, its bytes, and the pad that follows an
    odd length so the chunk after it begins on an even offset."""
    header = CHUNK_HEADER.pack({"tag": tag, "size": len(payload)})
    return header + payload + PADDING * (len(payload) % ALIGNMENT)


def wrapped(body: bytes) -> bytes:
    """The whole file a run of WAVE chunks makes up, inside the RIFF container that names the form."""
    return tagged(RIFF_MAGIC, WAVE_FORM + body)


def chunks(data: bytes) -> dict[bytes, bytes]:
    """Every chunk a run of them holds, keyed by tag, keeping the first where one tag appears twice."""
    held: dict[bytes, bytes] = {}
    cursor = Cursor(data)
    while cursor.remaining >= CHUNK_HEADER_BYTES:
        values = cursor.read(CHUNK_HEADER)
        payload = cursor.take_at_most(read_int(values, "size"))
        held.setdefault(read_bytes(values, "tag"), payload)
        cursor.skip(min(len(payload) % ALIGNMENT, cursor.remaining))

    return held


def formed(payload: bytes, form: bytes) -> dict[bytes, bytes]:
    """Every chunk a list holds, empty where the list states a form other than ``form``."""
    return chunks(payload[FORM_BYTES:]) if payload[:FORM_BYTES] == form else {}


def unwrapped(data: bytes) -> dict[bytes, bytes]:
    """Every chunk a WAVE file holds, read out of the RIFF container around them.

    Raises:
        ValueError: when the bytes stop inside the container, or state a magic or a form other than a
            RIFF file holding WAVE chunks.
    """
    cursor = Cursor(data)
    values = cursor.read(CHUNK_HEADER)
    magic = read_bytes(values, "tag")
    if magic != RIFF_MAGIC:
        raise ValueError(f"expected a {RIFF_MAGIC.decode()} container, the bytes state {magic!r}")

    body = cursor.take_at_most(read_int(values, "size"))
    form = body[:FORM_BYTES]
    if form != WAVE_FORM:
        raise ValueError(f"expected the {WAVE_FORM.decode()} form, the container states {form!r}")

    return chunks(body[FORM_BYTES:])


def required(held: Mapping[bytes, bytes], tag: bytes) -> bytes:
    """The chunk a file has to hold for its waveform to be read.

    Raises:
        ValueError: when the file holds no chunk under that tag.
    """
    payload = held.get(tag)
    if payload is None:
        raise ValueError(f"the file states no {tag.decode()!r} chunk")

    return payload

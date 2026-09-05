from __future__ import annotations

from collections.abc import Iterator, Sequence

from pydantic import BaseModel

from trackmod.binary.text import decode_name, encode_name
from trackmod.schema.config import FROZEN
from trackmod.trackers.it.spec.extensions import (
    BLOCK_LENGTH_BYTES,
    BLOCK_MAGIC_BYTES,
    CHANNEL_NAME_BYTES,
    CHANNEL_NAMES_MAGIC,
    PATTERN_NAME_BYTES,
    PATTERN_NAMES_MAGIC,
)
from trackmod.trackers.it.spec.flags import SpecialFlag

BLOCK_HEADER_BYTES = BLOCK_MAGIC_BYTES + BLOCK_LENGTH_BYTES


def named_block(magic: bytes, names: Sequence[str], *, width: int) -> bytes:
    """One block of fixed-width names, headed by its tag and the bytes that follow it.

    A file states each name in a field of its own width, so a set of them costs its own count times that
    width and a reader recovers them by cutting the block up again.
    """
    if not names:
        return b""

    payload = b"".join(encode_name(name, width) for name in names)
    return magic + len(payload).to_bytes(BLOCK_LENGTH_BYTES, "little") + payload


def stated_blocks(data: bytes) -> Iterator[tuple[bytes, bytes]]:
    """Each block a region states: its tag, and the bytes that follow the length it declares.

    The blocks run one after another, so walking them by their own lengths reaches every one — including
    a tag this library has no reading for, which is stepped over at the length it states.

    Trackers also place content of their own in this region — plugin settings and the properties a later
    writer keeps for itself — which is laid out as that writer pleases rather than as blocks. The walk
    therefore runs while the bytes describe whole blocks and stops where they stop doing so, which is
    what leaves the blocks a reader does recognise reachable in the files that carry them.
    """
    at = 0
    while at + BLOCK_HEADER_BYTES <= len(data):
        magic = data[at : at + BLOCK_MAGIC_BYTES]
        length = int.from_bytes(data[at + BLOCK_MAGIC_BYTES : at + BLOCK_HEADER_BYTES], "little")
        payload = data[at + BLOCK_HEADER_BYTES : at + BLOCK_HEADER_BYTES + length]
        if len(payload) < length:
            return

        yield magic, payload
        at += BLOCK_HEADER_BYTES + length


def block_names(data: bytes, magic: bytes, *, width: int) -> tuple[str, ...]:
    """The names the block tagged ``magic`` holds, empty where the region states no such block."""
    payload = next((held for tag, held in stated_blocks(data) if tag == magic), b"")
    return tuple(decode_name(payload[at : at + width]) for at in range(0, len(payload), width))


def block_bytes(names: Sequence[str], *, width: int) -> int:
    """How many bytes a set of names occupies, header included, which is none where there are none."""
    return BLOCK_HEADER_BYTES + width * len(names) if names else 0


class Extensions(BaseModel):
    """What this format's later writers append beyond the records Impulse Tracker itself laid out.

    ``channel_names`` and ``pattern_names`` are stated blocks with a shape worth reading, so they are
    read as the names they hold. ``history`` is the record of editing sessions a file may carry, and
    ``appended`` is whatever a writer put past the last record the header points at -- the properties
    OpenMPT keeps for itself among them. Both travel as the bytes they were found as, so a module read
    here and written back carries everything it arrived with while this library states only what it reads.
    """

    model_config = FROZEN

    channel_names: tuple[str, ...] = ()
    pattern_names: tuple[str, ...] = ()
    history: bytes = b""
    appended: bytes = b""

    @property
    def special(self) -> SpecialFlag:
        """The header switches these blocks ask for, which is what tells a reader they are there.

        An editing history is found by the switch alone, since nothing points at where it sits.
        """
        return SpecialFlag.HISTORY if self.history else SpecialFlag(0)

    @property
    def named_bytes(self) -> int:
        """How many bytes the stated blocks occupy between the offset tables and the records they head."""
        return (
            len(self.history)
            + block_bytes(self.channel_names, width=CHANNEL_NAME_BYTES)
            + block_bytes(self.pattern_names, width=PATTERN_NAME_BYTES)
        )

    def heading(self) -> bytes:
        """The blocks that sit between the offset tables and the first record they point at."""
        return (
            self.history
            + named_block(CHANNEL_NAMES_MAGIC, self.channel_names, width=CHANNEL_NAME_BYTES)
            + named_block(PATTERN_NAMES_MAGIC, self.pattern_names, width=PATTERN_NAME_BYTES)
        )

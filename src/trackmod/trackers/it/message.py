from __future__ import annotations

from typing import Final

from pydantic import BaseModel

from trackmod.binary.text import encode_text
from trackmod.schema.config import FROZEN
from trackmod.trackers.it.spec.flags import SpecialFlag

NO_MESSAGE: Final = 0


def message_data(message: str) -> bytes:
    """The bytes a song message occupies in a file, closed by the terminator a reader stops at.

    A message the settings leave empty occupies nothing at all, which is how a module states that it
    attaches none.
    """
    return encode_text(message) if message else b""


class MessageBlock(BaseModel):
    """A song message as the file stores it: the bytes, and the offset the header points at them with.

    The header reserves an offset and a length for the message alone, so the block is placed once the
    rest of the file has been laid out and the header states where it landed. A module attaching no
    message states a zero offset and a zero length, with the header's message switch left clear.
    """

    model_config = FROZEN

    data: bytes
    offset: int

    @classmethod
    def of(cls, message: str, *, start: int) -> MessageBlock:
        """The block ``message`` occupies when it is written at ``start``."""
        data = message_data(message)
        return cls(data=data, offset=start if data else NO_MESSAGE)

    @property
    def length(self) -> int:
        """How many bytes the header states the message takes."""
        return len(self.data)

    @property
    def special(self) -> SpecialFlag:
        """The header switches this block asks for."""
        return SpecialFlag.MESSAGE if self.data else SpecialFlag(NO_MESSAGE)

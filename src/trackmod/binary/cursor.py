from trackmod.binary.records.record import Record
from trackmod.binary.records.values import ArrayValue, FieldValue


class Cursor:
    """Walks a module's bytes from front to back, which is how every format here is laid out.

    A parser reads sections in the order the file stores them, so a cursor that remembers where it is
    keeps every offset out of the parsing code.
    """

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._position = 0

    @property
    def position(self) -> int:
        """How many bytes have been consumed."""
        return self._position

    @property
    def remaining(self) -> int:
        """How many bytes are left."""
        return len(self._data) - self._position

    @property
    def at_end(self) -> bool:
        """Whether every byte has been consumed."""
        return self.remaining == 0

    def take(self, count: int) -> bytes:
        """Consume and return the next ``count`` bytes.

        Raises:
            ValueError: when fewer than ``count`` bytes remain.
        """
        chunk = self.peek(count)
        self._position += count
        return chunk

    def peek(self, count: int) -> bytes:
        """Return the next ``count`` bytes without consuming them.

        Raises:
            ValueError: when fewer than ``count`` bytes remain.
        """
        if count < 0:
            raise ValueError(f"cannot read {count} bytes")

        if count > self.remaining:
            raise ValueError(f"needed {count} bytes at offset {self._position}, {self.remaining} remain")

        return self._data[self._position : self._position + count]

    def take_at_most(self, count: int) -> bytes:
        """Consume and return up to ``count`` bytes, stopping where the data ends.

        A file may state a section longer than it goes on to hold, and a player sounds the part that is
        there rather than refusing the file, so a reader following one needs to do the same.
        """
        return self.take(min(count, self.remaining))

    def peek_padded(self, count: int) -> bytes:
        """Return the next ``count`` bytes, padded with zeroes where the data ends.

        This reads a fixed record out of a file that stops inside it: the fields the data reaches are
        the ones it stated, and the rest read as the zeroes an empty record holds.
        """
        held = self.peek(min(count, self.remaining))
        return held + bytes(count - len(held))

    def skip(self, count: int) -> None:
        """Consume ``count`` bytes without returning them.

        Raises:
            ValueError: when fewer than ``count`` bytes remain.
        """
        self.take(count)

    def seek(self, position: int) -> None:
        """Move to an absolute byte offset.

        Raises:
            ValueError: when the offset falls outside the data.
        """
        if not 0 <= position <= len(self._data):
            raise ValueError(f"offset {position} falls outside {len(self._data)} bytes")

        self._position = position

    def read(self, record: Record) -> dict[str, FieldValue | ArrayValue]:
        """Consume one record's worth of bytes and unpack its described fields."""
        return record.unpack(self.take(record.size))

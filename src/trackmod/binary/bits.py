from trackmod.spec.width import BITS_PER_BYTE


class BitReader:
    """Reads variable-width fields from a byte stream, least significant bit first.

    A compressed waveform packs its values at a width that changes as it runs, so the reader keeps a
    running buffer of whole bytes and hands out whatever width is asked for next. Bytes are drawn in as
    the buffer runs dry, which is what makes one field cost a shift rather than a walk over its bits.
    """

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._index = 0
        self._buffer = 0
        self._available = 0

    def take(self, width: int) -> int:
        """The next ``width`` bits, as an unsigned integer.

        Raises:
            ValueError: when the stream holds fewer bits than were asked for.
        """
        while self._available < width:
            if self._index >= len(self._data):
                raise ValueError(f"the stream holds {self._available} bits, short of the {width} asked for")

            self._buffer |= self._data[self._index] << self._available
            self._index += 1
            self._available += BITS_PER_BYTE

        value = self._buffer & ((1 << width) - 1)
        self._buffer >>= width
        self._available -= width
        return value

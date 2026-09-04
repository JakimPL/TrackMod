from trackmod.core.samples.depth import BitDepth


class BitWriter:
    """Lays fields out the way a compressed block stores them, so a test can state one by hand."""

    def __init__(self) -> None:
        self._bits: list[int] = []

    def put(self, value: int, width: int) -> None:
        self._bits.extend((value >> index) & 1 for index in range(width))

    def block(self) -> bytes:
        padded = self._bits + [0] * (-len(self._bits) % 8)
        payload = bytes(
            sum(bit << index for index, bit in enumerate(padded[start : start + 8]))
            for start in range(0, len(padded), 8)
        )
        return len(payload).to_bytes(2, "little") + payload


def stated(differences: list[int], *, depth: BitDepth) -> bytes:
    """One block stating each difference at the width a block opens on.

    That width is one wider than the depth, and the extra bit is what announces a width change, so a
    difference is laid out in the depth's own bits and the bit above it stays clear.
    """
    writer = BitWriter()
    bits = int(depth)
    for difference in differences:
        writer.put(difference & ((1 << bits) - 1), bits + 1)

    return writer.block()

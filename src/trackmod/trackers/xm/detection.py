from trackmod.trackers.xm.spec.identity import (
    MAGIC,
    MAGIC_BYTES,
    MAGIC_INSTRUMENT,
    MAGIC_INSTRUMENT_BYTES,
)


def written_here(data: bytes) -> bool:
    """Whether the bytes hold a module of this format, which the text it opens with states.

    A file of this format opens with its name spelled out, so the leading text is what a reader goes by
    before it reads anything else.
    """
    return data[:MAGIC_BYTES] == MAGIC


def instrument_written_here(data: bytes) -> bool:
    """Whether the bytes hold one instrument stored on its own, which its own opening text states."""
    return data[:MAGIC_INSTRUMENT_BYTES] == MAGIC_INSTRUMENT

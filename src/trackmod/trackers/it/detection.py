from trackmod.trackers.it.spec.identity import MAGIC_INSTRUMENT, MAGIC_MODULE


def written_here(data: bytes) -> bool:
    """Whether the bytes hold a module of this format, which the four it opens with state.

    Every section of this format opens with a tag of its own, and the file opens with the module's, so
    the first four bytes are what a reader goes by before it reads anything else.
    """
    return data[: len(MAGIC_MODULE)] == MAGIC_MODULE


def instrument_written_here(data: bytes) -> bool:
    """Whether the bytes hold one instrument stored on its own, which its own opening tag states."""
    return data[: len(MAGIC_INSTRUMENT)] == MAGIC_INSTRUMENT

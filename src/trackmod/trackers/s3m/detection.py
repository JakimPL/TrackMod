from trackmod.trackers.s3m.spec.identity import MAGIC_MODULE, MAGIC_OFFSET


def written_here(data: bytes) -> bool:
    """Whether the bytes hold a module of this format, which the four at offset 44 state.

    This format spends its opening bytes on the song's name and states what it is behind them, so the
    tag sits inside the header rather than in front of it.
    """
    return data[MAGIC_OFFSET : MAGIC_OFFSET + len(MAGIC_MODULE)] == MAGIC_MODULE

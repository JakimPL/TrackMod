from enum import StrEnum, unique


@unique
class PcmEncoding(StrEnum):
    """How a format lays a waveform's frames out on disk.

    Absolute storage writes each frame's amplitude; delta storage writes successive differences and the
    player integrates them with a running sum in the stored width.
    """

    ABSOLUTE = "absolute"
    DELTA = "delta"

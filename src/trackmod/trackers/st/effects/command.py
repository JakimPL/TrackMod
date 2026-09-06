from enum import IntEnum, unique


@unique
class STEffect(IntEnum):
    """The effect commands this format numbers, printed as the single hexadecimal digit a cell holds.

    The command is four bits, and the trackers that wrote this format spent seven of the sixteen. Amiga
    ProTracker filled the rest and kept these seven at the numbers they hold here, which is why a song
    written under either reads the same. A cell holding one of the nine left over is kept as the bytes
    it carries, for whoever knows which tracker wrote them.
    """

    ARPEGGIO = 0x0
    PORTAMENTO_UP = 0x1
    PORTAMENTO_DOWN = 0x2
    POSITION_JUMP = 0xB
    SET_VOLUME = 0xC
    PATTERN_BREAK = 0xD
    SET_SPEED = 0xF

    @property
    def letter(self) -> str:
        """The character a tracker prints for this command."""
        return f"{self:X}"

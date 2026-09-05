from enum import IntEnum, unique
from typing import Final

DIGITS: Final = 10


@unique
class MODEffect(IntEnum):
    """The effect commands this format numbers, printed as the single hexadecimal digit a cell holds.

    The command is four bits, so this is the whole set — every tracker that came after widened it, and
    the trackers descended from this one kept these sixteen at the numbers they hold here.
    """

    ARPEGGIO = 0x0
    PORTAMENTO_UP = 0x1
    PORTAMENTO_DOWN = 0x2
    TONE_PORTAMENTO = 0x3
    VIBRATO = 0x4
    TONE_PORTAMENTO_VOLUME_SLIDE = 0x5
    VIBRATO_VOLUME_SLIDE = 0x6
    TREMOLO = 0x7
    SET_PANNING = 0x8
    SAMPLE_OFFSET = 0x9
    VOLUME_SLIDE = 0xA
    POSITION_JUMP = 0xB
    SET_VOLUME = 0xC
    PATTERN_BREAK = 0xD
    EXTENDED = 0xE
    SET_SPEED = 0xF

    @property
    def letter(self) -> str:
        """The character a tracker prints for this command."""
        if self < DIGITS:
            return chr(ord("0") + self)

        return chr(ord("A") + self - DIGITS)


@unique
class MODExtended(IntEnum):
    """The sub-commands the ``E`` effect selects with its high nibble.

    ``E8`` is left out: the trackers that wrote this format put different things there, so a cell
    carrying it is kept as the bytes it holds and read by whoever knows which tracker wrote them.
    """

    FILTER = 0x0
    FINE_PORTAMENTO_UP = 0x1
    FINE_PORTAMENTO_DOWN = 0x2
    GLISSANDO = 0x3
    VIBRATO_WAVEFORM = 0x4
    FINETUNE = 0x5
    PATTERN_LOOP = 0x6
    TREMOLO_WAVEFORM = 0x7
    RETRIGGER = 0x9
    FINE_VOLUME_UP = 0xA
    FINE_VOLUME_DOWN = 0xB
    NOTE_CUT = 0xC
    NOTE_DELAY = 0xD
    PATTERN_DELAY = 0xE
    INVERT_LOOP = 0xF

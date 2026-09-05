from enum import IntEnum, unique


@unique
class S3MEffect(IntEnum):
    """The effect commands this format numbers, printed as the letter each one counts from ``A``.

    Scream Tracker 3 spells its commands with letters and leaves gaps in the alphabet where it names
    nothing, so the numbers here are the positions the letters hold rather than a run.
    """

    SET_SPEED = 1
    POSITION_JUMP = 2
    PATTERN_BREAK = 3
    VOLUME_SLIDE = 4
    PORTAMENTO_DOWN = 5
    PORTAMENTO_UP = 6
    TONE_PORTAMENTO = 7
    VIBRATO = 8
    TREMOR = 9
    ARPEGGIO = 10
    VIBRATO_VOLUME_SLIDE = 11
    PORTAMENTO_VOLUME_SLIDE = 12
    SAMPLE_OFFSET = 15
    RETRIGGER = 17
    TREMOLO = 18
    EXTENDED = 19
    SET_TEMPO = 20
    FINE_VIBRATO = 21
    GLOBAL_VOLUME = 22
    SET_PANNING = 24

    @property
    def letter(self) -> str:
        """The letter a tracker prints for this command."""
        return chr(ord("A") + self - 1)


@unique
class S3MExtended(IntEnum):
    """The sub-commands the ``S`` effect selects with its high nibble."""

    FILTER = 0x0
    GLISSANDO = 0x1
    FINETUNE = 0x2
    VIBRATO_WAVEFORM = 0x3
    TREMOLO_WAVEFORM = 0x4
    PANNING = 0x8
    STEREO_CONTROL = 0xA
    PATTERN_LOOP = 0xB
    NOTE_CUT = 0xC
    NOTE_DELAY = 0xD
    PATTERN_DELAY = 0xE
    FUNK_REPEAT = 0xF

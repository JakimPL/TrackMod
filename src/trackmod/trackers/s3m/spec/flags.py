from enum import IntEnum, IntFlag, unique
from typing import Final


@unique
class HeaderFlag(IntFlag):
    """The song-wide switches the file header carries, most of them naming an older tracker's reading."""

    ST2_VIBRATO = 0x01
    ST2_TEMPO = 0x02
    AMIGA_SLIDES = 0x04
    ZERO_VOLUME_OPTIMISATION = 0x08
    AMIGA_LIMITS = 0x10
    ENABLE_FILTER = 0x20
    ST3_VOLUME_SLIDES = 0x40
    CUSTOM_DATA = 0x80


@unique
class SampleFlag(IntFlag):
    """The storage and looping switches an instrument record carries for its waveform."""

    LOOP = 0x01
    STEREO = 0x02
    SIXTEEN_BIT = 0x04


@unique
class RecordType(IntEnum):
    """What one instrument record holds, which decides how the rest of its eighty bytes read.

    A record of the first two kinds is read here: an empty slot keeps a song's numbering while it holds
    no waveform, and a sampled one carries the frames a cell sounds. The kinds above them describe an
    OPL patch by its registers instead of a waveform, which is a synthesiser this library sounds no
    part of.
    """

    EMPTY = 0
    SAMPLE = 1
    ADLIB_MELODY = 2
    ADLIB_BASS = 3
    ADLIB_SNARE = 4
    ADLIB_TOM = 5
    ADLIB_CYMBAL = 6
    ADLIB_HIHAT = 7


PANNING_STATED: Final = 0x20
PANNING_MASK: Final = 0x0F
PANNING_TABLE: Final = 0xFC

STEREO_MIXING: Final = 0x80
MIX_VOLUME_MASK: Final = 0x7F

CHANNEL_UNUSED: Final = 0xFF
CHANNEL_RIGHT: Final = 0x08
CHANNEL_SIDE_WIDTH: Final = 8

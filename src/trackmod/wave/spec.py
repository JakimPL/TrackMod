from collections.abc import Mapping
from typing import Final

from trackmod.binary.pcm.encoding import PcmEncoding
from trackmod.binary.pcm.sign import PcmSign
from trackmod.core.samples.depth import BitDepth

WAVE_EXTENSION: Final = ".wav"

RIFF_MAGIC: Final = b"RIFF"
WAVE_FORM: Final = b"WAVE"
INFO_FORM: Final = b"INFO"

LIST_TAG: Final = b"LIST"
FORMAT_TAG: Final = b"fmt "
DATA_TAG: Final = b"data"
SAMPLER_TAG: Final = b"smpl"
INSTRUMENT_TAG: Final = b"inst"
EXTRA_TAG: Final = b"xtra"
NAME_TAG: Final = b"INAM"

TAG_BYTES: Final = 4
FORM_BYTES: Final = 4
CHUNK_HEADER_BYTES: Final = 8
ALIGNMENT: Final = 2

FORMAT_CHUNK_BYTES: Final = 16
SAMPLER_CHUNK_BYTES: Final = 36
SAMPLER_LOOP_BYTES: Final = 24
INSTRUMENT_CHUNK_BYTES: Final = 7
EXTRA_CHUNK_BYTES: Final = 16

NAME_BYTES: Final = 32
FILENAME_BYTES: Final = 22

INTEGER_SAMPLES: Final = 1
NANOSECONDS: Final = 1_000_000_000

FORWARD_LOOP: Final = 0
PING_PONG_LOOP: Final = 1
MAX_LOOPS: Final = 2
SUSTAIN_LOOPS: Final = 2
LOOPS_FOREVER: Final = 0

PANNING_SET: Final = 0x20

LOWEST_KEY: Final = 0
HIGHEST_KEY: Final = 127
SOFTEST_VELOCITY: Final = 1
LOUDEST_VELOCITY: Final = 127
NO_FINETUNE: Final = 0
NO_GAIN: Final = 0

STORED_VOLUME_SCALE: Final = 4

DEFAULT_WAVEFORM: Final = 0
STORED_WAVEFORMS: Final[Mapping[int, int]] = {0: 0, 1: 3, 2: 1, 3: 4, 4: 2}
SHARED_WAVEFORMS: Final[Mapping[int, int]] = {stored: shared for shared, stored in STORED_WAVEFORMS.items()}

STORED_ENCODING: Final = PcmEncoding.ABSOLUTE
STORED_SIGNS: Final[Mapping[BitDepth, PcmSign]] = {
    BitDepth.EIGHT: PcmSign.UNSIGNED,
    BitDepth.SIXTEEN: PcmSign.SIGNED,
}

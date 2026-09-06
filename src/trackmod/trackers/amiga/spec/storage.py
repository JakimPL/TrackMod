from typing import Final

from trackmod.binary.pcm.encoding import PcmEncoding
from trackmod.binary.pcm.sign import PcmSign
from trackmod.core.samples.depth import BitDepth

PCM_ENCODING: Final = PcmEncoding.ABSOLUTE
PCM_SIGN: Final = PcmSign.SIGNED
PCM_DEPTH: Final = BitDepth.EIGHT

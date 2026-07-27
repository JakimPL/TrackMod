from pydantic import BaseModel

from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Count


class SizeReport(BaseModel):
    """How many bytes a module occupies, split by what spends them.

    ``headers`` is every record byte the file lays out, which is this format's
    :class:`~trackmod.module.storage.Storage` table read against the counts the song declares.
    ``patterns`` and ``pcm`` are what no table predicts: the packed cell streams and the waveforms.

    Callers working under a size budget need to know where the bytes go, and ``largest_pattern`` answers
    a separate question: both formats store a packed pattern's length in a 16-bit field, so the biggest
    single pattern decides whether a song can be written at all.

    A file holding one instrument on its own spends its every byte on records and waveforms, so both
    pattern counts read zero there.
    """

    model_config = FROZEN

    patterns: Count
    pcm: Count
    headers: Count
    largest_pattern: Count

    @property
    def total(self) -> int:
        """The size of the whole file."""
        return self.patterns + self.pcm + self.headers

from typing import Annotated

from pydantic import BaseModel, Field

from trackmod.schema.config import FROZEN
from trackmod.spec.width import BYTE_MAX
from trackmod.trackers.mod.dialect import Dialect


class MODSettings(BaseModel):
    """The song-wide values this format carries that the shared model leaves to each format.

    ``dialect`` is the tag a module is written under. A file read back carries the tag it held, so
    writing it again spells the same one; a song built from nothing leaves it unstated and the writer
    picks the tag that states the width the song holds.

    ``restart`` is the byte the header holds where a song resumes after its last position. Trackers of
    this lineage write a marker there — most often the full width of the order table — while an order
    list holds a position inside itself, so the byte a file stated is kept here and written back as it
    stood. A song built from nothing leaves it unstated and the writer states the position the order
    list holds.
    """

    model_config = FROZEN

    dialect: Dialect | None = None
    restart: Annotated[int, Field(ge=0, le=BYTE_MAX)] | None = None

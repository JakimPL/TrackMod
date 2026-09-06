from typing import Annotated

from pydantic import BaseModel, Field

from trackmod.schema.config import FROZEN
from trackmod.spec.width import BYTE_MAX


class STSettings(BaseModel):
    """The song-wide values this format carries that the shared model leaves to each format.

    ``tempo`` is the byte the header holds after the order count, where the trackers of this format
    wrote a speed of their own in units they each read their own way. A file read back carries the byte
    it held, so writing it again states the same one; a song built from nothing leaves it unstated and
    the writer states the byte every module of this format opens on.
    """

    model_config = FROZEN

    tempo: Annotated[int, Field(ge=0, le=BYTE_MAX)] | None = None

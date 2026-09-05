from __future__ import annotations

import numpy as np
from pydantic import BaseModel, model_validator

from trackmod.core.patterns.grid import Pattern
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.voices.voices import Voices
from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Channels


class Song(BaseModel):
    """A complete piece of tracker music, held in the terms every tracker format shares.

    Patterns are a flat list the order names positions in, and ``voices`` is the table the instrument
    column names positions in — either the samples a cell plays directly or the instruments that route
    keys onto samples, which is the choice each tracker makes and each format states. A song is
    self-contained: every reference it holds points inside itself.

    Every pattern is the same width, which is the contract formats that store one channel count for the
    whole module need.
    """

    model_config = FROZEN

    name: str
    channels: Channels
    patterns: tuple[Pattern, ...]
    order: OrderList
    voices: Voices
    playback: Playback

    @model_validator(mode="after")
    def _references_resolve(self) -> Song:
        for index, pattern in enumerate(self.patterns):
            if pattern.channels != self.channels:
                raise ValueError(
                    f"pattern {index} is {pattern.channels} channels wide, but the song declares {self.channels}"
                )

            named = int(np.max(pattern.instrument))
            if named >= self.voices.slots:
                raise ValueError(f"pattern {index} names voice {named} of {self.voices.slots}")

        for position, entry in enumerate(self.order.entries):
            if entry >= len(self.patterns):
                raise ValueError(f"order position {position} names pattern {entry} of {len(self.patterns)}")

        return self

    @property
    def rows(self) -> int:
        """How many rows the song plays in total, following its order list."""
        return sum(self.patterns[entry].rows for entry in self.order.entries)

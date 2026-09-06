from typing import Annotated

from pydantic import Field

from trackmod.spec.clock import MIN_SPEED, MIN_TEMPO
from trackmod.spec.grid import MIN_CHANNELS
from trackmod.spec.levels import (
    MAX_INSTRUMENT_VOLUME,
    MAX_PANNING,
    MAX_VIBRATO_UNIT,
    MAX_VOLUME,
    MIN_FADEOUT,
    MIN_INSTRUMENT_VOLUME,
    MIN_PANNING,
    MIN_VIBRATO_UNIT,
    MIN_VOLUME,
)
from trackmod.spec.volumes import MAX_AMOUNT
from trackmod.spec.width import SIGNED_BYTE_MAX, SIGNED_BYTE_MIN

Index = Annotated[int, Field(ge=0)]
Count = Annotated[int, Field(ge=0)]
Offset = Annotated[int, Field(ge=0)]
Tick = Annotated[int, Field(ge=0)]
Frames = Annotated[int, Field(ge=0)]
Rate = Annotated[int, Field(gt=0)]

Volume = Annotated[int, Field(ge=MIN_VOLUME, le=MAX_VOLUME)]
VolumeAmount = Annotated[int, Field(ge=0, le=MAX_AMOUNT)]
Panning = Annotated[int, Field(ge=MIN_PANNING, le=MAX_PANNING)]
InstrumentVolume = Annotated[int, Field(ge=MIN_INSTRUMENT_VOLUME, le=MAX_INSTRUMENT_VOLUME)]
Fadeout = Annotated[int, Field(ge=MIN_FADEOUT)]
VibratoUnit = Annotated[int, Field(ge=MIN_VIBRATO_UNIT, le=MAX_VIBRATO_UNIT)]
Transposition = Annotated[int, Field(ge=SIGNED_BYTE_MIN, le=SIGNED_BYTE_MAX)]

Speed = Annotated[int, Field(ge=MIN_SPEED)]
Tempo = Annotated[int, Field(ge=MIN_TEMPO)]

Channels = Annotated[int, Field(ge=MIN_CHANNELS)]

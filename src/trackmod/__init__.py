import importlib.metadata

from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.transfer import combine, extract, units
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.song import Song
from trackmod.core.voices.convert import flattened, raised
from trackmod.core.voices.voices import InstrumentVoices, SampleVoices, Voices
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import LimitError
from trackmod.limits.violation import Violation
from trackmod.module.instrument import InstrumentFile
from trackmod.module.protocol import TrackerModule
from trackmod.trackers.it.instrument_file import ITInstrumentFile
from trackmod.trackers.it.module import ITModule
from trackmod.trackers.mod.module import MODModule
from trackmod.trackers.registry import (
    EXTENSIONS,
    INSTRUMENT_EXTENSIONS,
    MODULE_EXTENSIONS,
    detected,
    load_module,
    load_voices,
    parse_module,
    parse_voices,
)
from trackmod.trackers.s3m.module import S3MModule
from trackmod.trackers.st.module import STModule
from trackmod.trackers.xm.instrument_file import XMInstrumentFile
from trackmod.trackers.xm.module import XMModule
from trackmod.wave.parser import load_sample, parse_sample
from trackmod.wave.writer import save_sample, write_sample

__version__ = importlib.metadata.version("trackmod")

__all__ = [
    "EXTENSIONS",
    "INSTRUMENT_EXTENSIONS",
    "MODULE_EXTENSIONS",
    "BitDepth",
    "Compliance",
    "ITInstrumentFile",
    "ITModule",
    "Instrument",
    "InstrumentFile",
    "InstrumentUnit",
    "InstrumentVoices",
    "LimitError",
    "Loop",
    "LoopMode",
    "MODModule",
    "S3MModule",
    "STModule",
    "Sample",
    "SampleVoices",
    "Song",
    "TrackerModule",
    "Violation",
    "Voices",
    "XMInstrumentFile",
    "XMModule",
    "combine",
    "detected",
    "extract",
    "flattened",
    "load_module",
    "load_sample",
    "load_voices",
    "parse_module",
    "parse_sample",
    "parse_voices",
    "raised",
    "save_sample",
    "units",
    "write_sample",
]

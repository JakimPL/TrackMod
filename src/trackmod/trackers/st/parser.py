from trackmod.binary.cursor import Cursor
from trackmod.binary.records.values import read_bytes, read_int
from trackmod.binary.text import decode_name
from trackmod.core.patterns.repair import voiced_patterns
from trackmod.core.repairs.report import Repairs
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.repair import repaired_order
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import SampleVoices
from trackmod.trackers.amiga.layout.file import MODULE_NAME
from trackmod.trackers.amiga.reading import (
    held_samples,
    pattern_count,
    read_order,
    read_patterns,
    read_records,
    read_samples,
)
from trackmod.trackers.amiga.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.amiga.spec.sizes import MODULE_NAME_BYTES
from trackmod.trackers.st.layout.file import SEQUENCE
from trackmod.trackers.st.settings import STSettings
from trackmod.trackers.st.spec.ranges import (
    CHANNELS,
    LOOP_BEGIN_UNIT,
    MAX_PATTERNS,
    PATTERN_BYTES,
)
from trackmod.trackers.st.spec.sizes import FILE_HEADER_BYTES, SAMPLE_SLOTS


class ModuleReader:
    """Walks a fifteen-sample Soundtracker file, whose header is a fixed slab and whose body follows it.

    The width is settled before anything else is read, and this format settles it the only way it can:
    every module of it plays the four channels its machine had, so the reader knows the width without
    the file stating it.
    """

    def __init__(self, data: bytes) -> None:
        self._repairs = Repairs()
        self._name = MODULE_NAME.unpack(data[:MODULE_NAME_BYTES])
        self._records = read_records(data, slots=SAMPLE_SLOTS)
        self._sequence = SEQUENCE.unpack(data[FILE_HEADER_BYTES - SEQUENCE.size : FILE_HEADER_BYTES])
        self._order = OrderList(entries=read_order(self._sequence, repairs=self._repairs))
        cursor = Cursor(data)
        cursor.seek(FILE_HEADER_BYTES)
        self._patterns = read_patterns(
            cursor,
            count=self._pattern_count(data),
            channels=CHANNELS,
            repairs=self._repairs,
        )
        self._samples = read_samples(cursor, self._records, begin_unit=LOOP_BEGIN_UNIT, repairs=self._repairs)

    def song(self) -> Song:
        """The format-agnostic content the file carries, with whatever it stated out of range drawn in."""
        voices = SampleVoices(samples=held_samples(self._samples, self._patterns))
        song = Song(
            name=decode_name(read_bytes(self._name, "name")),
            channels=CHANNELS,
            patterns=voiced_patterns(self._patterns, slots=voices.slots, repairs=self._repairs),
            order=repaired_order(self._order, patterns=len(self._patterns), subject="song", repairs=self._repairs),
            voices=voices,
            playback=Playback(speed=DEFAULT_SPEED, tempo=DEFAULT_TEMPO),
        )
        self._repairs.warn()
        return song

    def settings(self) -> STSettings:
        """The song-wide value this format adds: the byte its header holds a speed of its own in."""
        return STSettings(tempo=read_int(self._sequence, "tempo"))

    def _pattern_count(self, data: bytes) -> int:
        """How many patterns the file holds, at the one width every module of this format plays."""
        return pattern_count(
            data,
            order=self._order,
            records=self._records,
            header_bytes=FILE_HEADER_BYTES,
            pattern_bytes=PATTERN_BYTES,
            maximum=MAX_PATTERNS,
            repairs=self._repairs,
        )

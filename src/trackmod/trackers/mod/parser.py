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
from trackmod.trackers.amiga.spec.cells import CELL_BYTES
from trackmod.trackers.amiga.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.amiga.spec.ranges import PATTERN_ROWS
from trackmod.trackers.amiga.spec.sizes import MODULE_NAME_BYTES
from trackmod.trackers.mod.layout.file import SEQUENCE
from trackmod.trackers.mod.settings import MODSettings
from trackmod.trackers.mod.spec.ranges import EXTENDED_MAX_PATTERNS, LOOP_BEGIN_UNIT
from trackmod.trackers.mod.spec.sizes import FILE_HEADER_BYTES, SAMPLE_SLOTS
from trackmod.trackers.mod.tag import detected


class ModuleReader:
    """Walks an Amiga ProTracker file, whose header is a fixed slab and whose body follows it in order.

    The tag settles the channel count before anything else is read, because the file states the width
    nowhere else: two modules of the same length hold different music depending on which tag they carry.
    """

    def __init__(self, data: bytes) -> None:
        self._repairs = Repairs()
        self._dialect = detected(data)
        self._name = MODULE_NAME.unpack(data[:MODULE_NAME_BYTES])
        self._records = read_records(data, slots=SAMPLE_SLOTS)
        self._sequence = SEQUENCE.unpack(data[FILE_HEADER_BYTES - SEQUENCE.size : FILE_HEADER_BYTES])
        self._order = self._read_order()
        cursor = Cursor(data)
        cursor.seek(FILE_HEADER_BYTES)
        self._patterns = read_patterns(
            cursor,
            count=self._pattern_count(data),
            channels=self._dialect.channels,
            repairs=self._repairs,
        )
        self._samples = read_samples(cursor, self._records, begin_unit=LOOP_BEGIN_UNIT, repairs=self._repairs)

    def song(self) -> Song:
        """The format-agnostic content the file carries, with whatever it stated out of range drawn in."""
        voices = SampleVoices(samples=held_samples(self._samples, self._patterns))
        song = Song(
            name=decode_name(read_bytes(self._name, "name")),
            channels=self._dialect.channels,
            patterns=voiced_patterns(self._patterns, slots=voices.slots, repairs=self._repairs),
            order=repaired_order(self._order, patterns=len(self._patterns), subject="song", repairs=self._repairs),
            voices=voices,
            playback=Playback(speed=DEFAULT_SPEED, tempo=DEFAULT_TEMPO),
        )
        self._repairs.warn()
        return song

    def settings(self) -> MODSettings:
        """The song-wide values this format adds: the dialect its tag names and the restart byte it held."""
        return MODSettings(dialect=self._dialect, restart=read_int(self._sequence, "restart"))

    def _read_order(self) -> OrderList:
        """The played order list, whose restart position is drawn inside the positions it names."""
        entries = read_order(self._sequence, repairs=self._repairs)
        restart = read_int(self._sequence, "restart")
        return OrderList(entries=entries, restart=min(restart, max(len(entries) - 1, 0)))

    def _pattern_count(self, data: bytes) -> int:
        """How many patterns the file holds, at the width the tag states."""
        return pattern_count(
            data,
            order=self._order,
            records=self._records,
            header_bytes=FILE_HEADER_BYTES,
            pattern_bytes=PATTERN_ROWS * self._dialect.channels * CELL_BYTES,
            maximum=EXTENDED_MAX_PATTERNS,
            repairs=self._repairs,
        )

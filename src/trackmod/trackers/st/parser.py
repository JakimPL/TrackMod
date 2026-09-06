from typing import Final

from trackmod.binary.cursor import Cursor
from trackmod.binary.records.values import RecordValues, read_bytes, read_int
from trackmod.binary.text import decode_name
from trackmod.core.patterns.grid import Pattern
from trackmod.core.patterns.repair import voiced_patterns
from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.repair import repaired_order
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import SampleVoices
from trackmod.spec.grid import EMPTY
from trackmod.trackers.amiga.layout.file import MODULE_NAME
from trackmod.trackers.amiga.layout.sample import SAMPLE_HEADER
from trackmod.trackers.amiga.patterns.parser import unpack_pattern
from trackmod.trackers.amiga.samples.parser import parse_sample, stated_frames, stored_bytes
from trackmod.trackers.amiga.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.amiga.spec.ranges import MAX_ORDERS, PATTERN_ROWS
from trackmod.trackers.amiga.spec.sizes import MODULE_NAME_BYTES, SAMPLE_TABLE_OFFSET
from trackmod.trackers.st.layout.file import SEQUENCE
from trackmod.trackers.st.settings import STSettings
from trackmod.trackers.st.spec.ranges import (
    CHANNELS,
    LOOP_BEGIN_UNIT,
    MAX_PATTERNS,
    PATTERN_BYTES,
)
from trackmod.trackers.st.spec.sizes import FILE_HEADER_BYTES, SAMPLE_SLOTS

NO_PATTERNS: Final = 0


class ModuleReader:
    """Walks a fifteen-sample Soundtracker file, whose header is a fixed slab and whose body follows it.

    The width is settled before anything else is read, and this format settles it the only way it can:
    every module of it plays the four channels its machine had, so the reader knows the width without
    the file stating it.
    """

    def __init__(self, data: bytes) -> None:
        self._repairs = Repairs()
        self._name = MODULE_NAME.unpack(data[:MODULE_NAME_BYTES])
        self._records = self._read_records(data)
        self._sequence = SEQUENCE.unpack(data[FILE_HEADER_BYTES - SEQUENCE.size : FILE_HEADER_BYTES])
        self._order = self._read_order()
        cursor = Cursor(data)
        cursor.seek(FILE_HEADER_BYTES)
        self._patterns = self._read_patterns(cursor, count=self._pattern_count(data))
        self._samples = self._read_samples(cursor)

    def song(self) -> Song:
        """The format-agnostic content the file carries, with whatever it stated out of range drawn in."""
        voices = SampleVoices(samples=self._held_samples())
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

    def _read_records(self, data: bytes) -> tuple[RecordValues, ...]:
        table = Cursor(data)
        table.seek(SAMPLE_TABLE_OFFSET)
        return tuple(table.read(SAMPLE_HEADER) for _ in range(SAMPLE_SLOTS))

    def _read_order(self) -> OrderList:
        """The played order list, whose length is drawn inside the table it sits in."""
        stated = read_int(self._sequence, "order_count")
        count = min(stated, MAX_ORDERS)
        if count != stated:
            self._repairs.made(
                f"an order of {stated} positions read as the {MAX_ORDERS} the table holds",
                subject="song",
            )

        return OrderList(entries=tuple(read_bytes(self._sequence, "orders")[:count]))

    def _pattern_count(self, data: bytes) -> int:
        """How many patterns the file holds, which it states in two ways that can disagree.

        The order table names the highest one a song plays, and the length left between the header and
        the waveforms holds however many were stored — a module carrying patterns its order never
        reaches has more than it names. Taking the larger keeps both, and reading the waveforms at the
        right offset depends on it.

        The room left between the header and the waveforms is what bounds the pair, because a table
        naming more patterns than the file holds would otherwise read the waveforms as music. The last
        pattern the room reaches counts even where the file stops inside it, so a file cut short still
        gives up the music it holds.
        """
        named = max((entry + 1 for entry in self._order.entries), default=NO_PATTERNS)
        waveforms = sum(stored_bytes(values) for values in self._records)
        room = max(len(data) - FILE_HEADER_BYTES - waveforms, 0)
        counted = min(max(named, room // PATTERN_BYTES), MAX_PATTERNS)
        reached = -(-room // PATTERN_BYTES)
        if counted <= reached:
            return counted

        self._repairs.made(f"an order naming {counted} patterns read as the {reached} the file holds", subject="song")
        return reached

    def _read_patterns(self, cursor: Cursor, *, count: int) -> tuple[Pattern, ...]:
        return tuple(
            unpack_pattern(
                cursor,
                rows=PATTERN_ROWS,
                channels=CHANNELS,
                subject=f"pattern {index}",
                repairs=self._repairs,
            )
            for index in range(count)
        )

    def _read_samples(self, cursor: Cursor) -> tuple[Sample, ...]:
        return tuple(
            parse_sample(
                values,
                stated_frames(cursor, values, subject=f"sample {slot}", repairs=self._repairs),
                begin_unit=LOOP_BEGIN_UNIT,
                subject=f"sample {slot}",
                repairs=self._repairs,
            )
            for slot, values in enumerate(self._records)
        )

    def _held_samples(self) -> tuple[Sample, ...]:
        """The slots a song keeps: every one up to the last the file states something about.

        The file writes fifteen records whatever it fills. A slot states something where it holds a
        waveform, where a cell names it, or where it carries a name — the trackers of this format wrote
        the sample library a waveform came from into that field, so a named slot holding nothing is
        still text the file carries. The trailing slots past all of that state nothing and are left out,
        while the empty slots before them stay, because the cells number their samples by position.
        """
        return self._samples[: max(self._sounded(), self._addressed(), self._named())]

    def _sounded(self) -> int:
        return max((slot + 1 for slot, sample in enumerate(self._samples) if sample.frames), default=0)

    def _named(self) -> int:
        return max((slot + 1 for slot, sample in enumerate(self._samples) if sample.name), default=0)

    def _addressed(self) -> int:
        highest = max(
            (int(pattern.instrument.max()) for pattern in self._patterns if pattern.instrument.size),
            default=EMPTY,
        )
        return highest + 1

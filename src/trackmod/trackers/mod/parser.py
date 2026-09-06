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
from trackmod.trackers.mod.layout.file import MODULE_NAME, SEQUENCE
from trackmod.trackers.mod.layout.sample import SAMPLE_HEADER
from trackmod.trackers.mod.patterns.parser import unpack_pattern
from trackmod.trackers.mod.samples.parser import parse_sample, stated_frames, stored_bytes
from trackmod.trackers.mod.settings import MODSettings
from trackmod.trackers.mod.spec.cells import CELL_BYTES
from trackmod.trackers.mod.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.mod.spec.ranges import (
    EXTENDED_MAX_PATTERNS,
    MAX_ORDERS,
    PATTERN_ROWS,
)
from trackmod.trackers.mod.spec.sizes import (
    FILE_HEADER_BYTES,
    MODULE_NAME_BYTES,
    SAMPLE_SLOTS,
    SAMPLE_TABLE_OFFSET,
)
from trackmod.trackers.mod.tag import detected

NO_PATTERNS = 0


class ModuleReader:
    """Walks an Amiga ProTracker file, whose header is a fixed slab and whose body follows it in order.

    The tag settles the channel count before anything else is read, because the file states the width
    nowhere else: two modules of the same length hold different music depending on which tag they carry.
    """

    def __init__(self, data: bytes) -> None:
        self._repairs = Repairs()
        self._dialect = detected(data)
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

    def _read_records(self, data: bytes) -> tuple[RecordValues, ...]:
        table = Cursor(data)
        table.seek(SAMPLE_TABLE_OFFSET)
        return tuple(table.read(SAMPLE_HEADER) for _ in range(SAMPLE_SLOTS))

    def _read_order(self) -> OrderList:
        """The played order list, whose length and restart position are drawn inside the table they sit in."""
        stated = read_int(self._sequence, "order_count")
        count = min(stated, MAX_ORDERS)
        if count != stated:
            self._repairs.made(
                f"an order of {stated} positions read as the {MAX_ORDERS} the table holds",
                subject="song",
            )

        entries = tuple(read_bytes(self._sequence, "orders")[:count])
        restart = read_int(self._sequence, "restart")
        return OrderList(entries=entries, restart=min(restart, max(len(entries) - 1, 0)))

    def _pattern_count(self, data: bytes) -> int:
        """How many patterns the file holds, which it states in two ways that disagree.

        The order table names the highest one a song plays, and the length left between the header and
        the waveforms holds however many were stored — a module carrying patterns its order never
        reaches has more than it names. Taking the larger keeps both, and reading the waveforms at the
        right offset depends on it.

        The room left between the header and the waveforms is what bounds the pair, because a table
        naming more patterns than the file holds would otherwise read the waveforms as music. The last
        pattern the room reaches counts even where the file stops inside it, so a file cut short still
        gives up the music it holds. Only the positions a song plays name a pattern: trackers of this
        lineage leave stale entries past them, and shortening a song leaves the table as it stood.
        """
        named = max((entry + 1 for entry in self._order.entries), default=NO_PATTERNS)
        waveforms = sum(stored_bytes(values) for values in self._records)
        room = max(len(data) - FILE_HEADER_BYTES - waveforms, 0)
        counted = min(max(named, room // self._pattern_bytes), EXTENDED_MAX_PATTERNS)
        reached = -(-room // self._pattern_bytes)
        if counted <= reached:
            return counted

        self._repairs.made(f"an order naming {counted} patterns read as the {reached} the file holds", subject="song")
        return reached

    @property
    def _pattern_bytes(self) -> int:
        """How many bytes one whole pattern occupies, at the width the tag states."""
        return PATTERN_ROWS * self._dialect.channels * CELL_BYTES

    def _read_patterns(self, cursor: Cursor, *, count: int) -> tuple[Pattern, ...]:
        return tuple(
            unpack_pattern(
                cursor,
                rows=PATTERN_ROWS,
                channels=self._dialect.channels,
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
                subject=f"sample {slot}",
                repairs=self._repairs,
            )
            for slot, values in enumerate(self._records)
        )

    def _held_samples(self) -> tuple[Sample, ...]:
        """The slots a song keeps: every one up to the last the file states something about.

        The file writes thirty-one records whatever it fills. A slot states something where it holds a
        waveform, where a cell names it, or where it carries a name — trackers of this lineage wrote
        liner notes into the sample names, so a named slot holding nothing is still text the file
        carries. The trailing slots past all of that state nothing and are left out, while the empty
        slots before them stay, because the cells number their samples by position.
        """
        return self._samples[: max(self._sounded(), self._named(), self._titled())]

    def _sounded(self) -> int:
        return max((slot + 1 for slot, sample in enumerate(self._samples) if sample.frames), default=0)

    def _titled(self) -> int:
        return max((slot + 1 for slot, sample in enumerate(self._samples) if sample.name), default=0)

    def _named(self) -> int:
        highest = max(
            (int(pattern.instrument.max()) for pattern in self._patterns if pattern.instrument.size),
            default=EMPTY,
        )
        return highest + 1

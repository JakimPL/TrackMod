import struct

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
from trackmod.spec.grid import MIN_CHANNELS
from trackmod.trackers.s3m.channels import stated_width
from trackmod.trackers.s3m.layout.file import FILE_HEADER
from trackmod.trackers.s3m.layout.instrument import INSTRUMENT_RECORD
from trackmod.trackers.s3m.panning import shared_panning
from trackmod.trackers.s3m.parapointers import pointed
from trackmod.trackers.s3m.patterns.parser import unpack_pattern
from trackmod.trackers.s3m.samples.parser import frame_sign, parse_sample, stated_frames
from trackmod.trackers.s3m.settings import S3MSettings
from trackmod.trackers.s3m.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.s3m.spec.flags import (
    MIX_VOLUME_MASK,
    PANNING_MASK,
    PANNING_STATED,
    PANNING_TABLE,
    STEREO_MIXING,
    HeaderFlag,
)
from trackmod.trackers.s3m.spec.identity import MAGIC_MODULE
from trackmod.trackers.s3m.spec.orders import ORDER_SEPARATOR, ORDER_TERMINATOR
from trackmod.trackers.s3m.spec.ranges import MIN_SPEED, MIN_TEMPO, PATTERN_ROWS
from trackmod.trackers.s3m.spec.sizes import (
    CHANNELS_STORED,
    ORDER_BYTES,
    PARAPOINTER_BYTES,
)

EMPTY_PATTERN_POINTER = 0


class ModuleReader:
    """Walks a Scream Tracker 3 file, following the two tables of paragraph numbers that head it.

    Every record, pattern and waveform is found by the paragraph it opens on rather than by walking the
    file, so a reader needs the tables and nothing else to reach any block. The header states the width
    of the module in its channel settings, which is what says how wide the cells of every pattern read.
    """

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._repairs = Repairs()
        cursor = Cursor(data)
        self._header = cursor.read(FILE_HEADER)
        if read_bytes(self._header, "magic") != MAGIC_MODULE:
            raise ValueError("data does not open with the Scream Tracker 3 module tag")

        self._order = self._read_order(cursor)
        self._sample_offsets = self._read_table(cursor, "sample_count")
        self._pattern_offsets = self._read_table(cursor, "pattern_count")
        self._panning = self._read_panning(cursor)
        self._channels = max(stated_width(self._settings_table), MIN_CHANNELS)

    def song(self) -> Song:
        """The format-agnostic content the file carries, with whatever it stated out of range drawn in."""
        voices = SampleVoices(samples=self._samples())
        patterns = self._patterns()
        song = Song(
            name=decode_name(read_bytes(self._header, "name")),
            channels=self._channels,
            patterns=voiced_patterns(patterns, slots=voices.slots, repairs=self._repairs),
            order=repaired_order(self._order, patterns=len(patterns), subject="song", repairs=self._repairs),
            voices=voices,
            playback=self._playback(),
        )
        self._repairs.warn()
        return song

    def settings(self) -> S3MSettings:
        """The song-wide values this format adds, as the header states them."""
        mixing = read_int(self._header, "mix_volume")
        return S3MSettings(
            global_volume=read_int(self._header, "global_volume"),
            mix_volume=mixing & MIX_VOLUME_MASK,
            stereo=bool(mixing & STEREO_MIXING),
            flags=HeaderFlag(read_int(self._header, "flags")),
            channels=self._settings_table,
            channel_panning=self._panning,
            created_with=read_int(self._header, "created_with"),
        )

    @property
    def _settings_table(self) -> tuple[int, ...]:
        return tuple(read_bytes(self._header, "channel_settings"))

    def _playback(self) -> Playback:
        """The clock the file starts on, with a speed or a tempo below its floor read as the default."""
        return Playback(
            speed=self._clock("speed", floor=MIN_SPEED, default=DEFAULT_SPEED),
            tempo=self._clock("tempo", floor=MIN_TEMPO, default=DEFAULT_TEMPO),
        )

    def _clock(self, field: str, *, floor: int, default: int) -> int:
        stated = read_int(self._header, field)
        if stated >= floor:
            return stated

        self._repairs.made(f"{field} {stated} read as {default}", subject="song")
        return default

    def _read_order(self, cursor: Cursor) -> OrderList:
        """The played order list, which holds the positions naming a pattern rather than a marker.

        The table marks two things beside its positions: one to step over, and the end of a song. A file
        holding further positions past an end carries a section a player sounds as a piece of its own,
        and every one of them is kept here, so the order list holds all the music the table names.
        """
        raw = cursor.take(ORDER_BYTES * read_int(self._header, "order_count"))
        return OrderList(entries=tuple(entry for entry in raw if entry not in (ORDER_SEPARATOR, ORDER_TERMINATOR)))

    def _read_table(self, cursor: Cursor, count_field: str) -> tuple[int, ...]:
        count = read_int(self._header, count_field)
        pointers = struct.unpack(f"<{count}H", cursor.take(PARAPOINTER_BYTES * count))
        return tuple(pointed(pointer) for pointer in pointers)

    def _read_panning(self, cursor: Cursor) -> tuple[int | None, ...] | None:
        """Where each channel opens on the stereo field, where the header says the block follows.

        Each entry reserves a bit for whether it states a position at all, so a channel claiming none
        opens on the side its own mixer slot puts it.
        """
        if read_int(self._header, "default_panning") != PANNING_TABLE:
            return None

        stated = cursor.take_at_most(CHANNELS_STORED)
        if len(stated) < CHANNELS_STORED:
            return None

        return tuple(shared_panning(entry & PANNING_MASK) if entry & PANNING_STATED else None for entry in stated)

    def _samples(self) -> tuple[Sample, ...]:
        return tuple(
            parse_sample(
                values,
                stated_frames(values, self._data, subject=f"sample {index}", repairs=self._repairs),
                sign=frame_sign(read_int(self._header, "frame_format")),
                subject=f"sample {index}",
                repairs=self._repairs,
            )
            for index, values in enumerate(self._records())
        )

    def _records(self) -> tuple[RecordValues, ...]:
        return tuple(INSTRUMENT_RECORD.unpack(self._data[offset:]) for offset in self._sample_offsets)

    def _patterns(self) -> tuple[Pattern, ...]:
        """Every pattern the order list can name, in the order the table numbers them.

        A pointer of zero names a pattern the file stores nowhere, which a tracker plays as a whole
        empty pattern -- so the slot is filled with silence rather than read from the file's own opening
        bytes.
        """
        patterns = []
        for index, offset in enumerate(self._pattern_offsets):
            if offset == EMPTY_PATTERN_POINTER:
                patterns.append(Pattern.empty(rows=PATTERN_ROWS, channels=self._channels))
                continue

            cursor = Cursor(self._data)
            cursor.seek(offset)
            patterns.append(
                unpack_pattern(
                    cursor,
                    rows=PATTERN_ROWS,
                    channels=self._channels,
                    subject=f"pattern {index}",
                    repairs=self._repairs,
                )
            )

        return tuple(patterns)

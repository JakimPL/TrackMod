import struct

from trackmod.binary.cursor import Cursor
from trackmod.binary.records.record import Record
from trackmod.binary.records.values import RecordValues, read_bytes, read_int
from trackmod.binary.text import decode_name, decode_text
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.repair import routed_within
from trackmod.core.patterns.grid import Pattern
from trackmod.core.patterns.repair import voiced_patterns
from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.repair import repaired_order
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import InstrumentVoices, SampleVoices, Voices
from trackmod.spec.grid import MIN_CHANNELS
from trackmod.trackers.it.addressing import names_instruments
from trackmod.trackers.it.extensions import Extensions, block_names
from trackmod.trackers.it.instruments.parser import parse_instrument
from trackmod.trackers.it.layout.file import FILE_HEADER
from trackmod.trackers.it.layout.instrument import INSTRUMENT_HEADER
from trackmod.trackers.it.layout.pattern import PATTERN_HEADER
from trackmod.trackers.it.layout.sample import SAMPLE_HEADER
from trackmod.trackers.it.patterns.parser import unpack_pattern
from trackmod.trackers.it.samples.parser import read_sample, stored_end
from trackmod.trackers.it.settings import ITSettings
from trackmod.trackers.it.spec.defaults import DEFAULT_MESSAGE
from trackmod.trackers.it.spec.extensions import (
    CHANNEL_NAME_BYTES,
    CHANNEL_NAMES_MAGIC,
    HISTORY_COUNT_BYTES,
    HISTORY_ENTRY_BYTES,
    PATTERN_NAME_BYTES,
    PATTERN_NAMES_MAGIC,
)
from trackmod.trackers.it.spec.flags import HeaderFlag, SpecialFlag
from trackmod.trackers.it.spec.identity import MAGIC_MODULE
from trackmod.trackers.it.spec.orders import ORDER_SEPARATOR, ORDER_TERMINATOR
from trackmod.trackers.it.spec.ranges import DEFAULT_ROWS, EMPTY_PATTERN_OFFSET
from trackmod.trackers.it.spec.sizes import (
    INSTRUMENT_HEADER_BYTES,
    OFFSET_TABLE_ENTRY_BYTES,
    PATTERN_HEADER_BYTES,
    SAMPLE_HEADER_BYTES,
)


class ModuleReader:
    """Walks an Impulse Tracker file, following the three offset tables that head it."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._repairs = Repairs()
        cursor = Cursor(data)
        self._header = cursor.read(FILE_HEADER)
        if read_bytes(self._header, "magic") != MAGIC_MODULE:
            raise ValueError("data does not open with the Impulse Tracker module tag")

        self._order = self._read_order(cursor)
        self._instrument_offsets = self._read_table(cursor, "instrument_count")
        self._sample_offsets = self._read_table(cursor, "sample_count")
        self._pattern_offsets = self._read_table(cursor, "pattern_count")
        self._tables_end = cursor.position

    def song(self) -> Song:
        """The format-agnostic content the file carries, with whatever it stated out of range drawn in."""
        patterns = self._patterns()
        channels = max((pattern.channels for pattern in patterns), default=1)
        voices = self._voices()
        song = Song(
            name=decode_name(read_bytes(self._header, "name")),
            channels=channels,
            patterns=self._voiced(patterns, channels=channels, slots=voices.slots),
            order=repaired_order(self._order, patterns=len(patterns), subject="song", repairs=self._repairs),
            voices=voices,
            playback=Playback(
                speed=read_int(self._header, "speed"),
                tempo=read_int(self._header, "tempo"),
            ),
        )
        self._repairs.warn()
        return song

    def settings(self) -> ITSettings:
        """The song-wide values this format adds, as the header states them."""
        return ITSettings(
            global_volume=read_int(self._header, "global_volume"),
            mix_volume=read_int(self._header, "mix_volume"),
            panning_separation=read_int(self._header, "panning_separation"),
            channel_panning=tuple(read_bytes(self._header, "channel_pan")),
            channel_volume=tuple(read_bytes(self._header, "channel_volume")),
            flags=HeaderFlag(read_int(self._header, "flags")),
            message=self._message(),
            extensions=self._extensions(),
            created_with=read_int(self._header, "created_with"),
        )

    def _voiced(self, patterns: tuple[Pattern, ...], *, channels: int, slots: int) -> tuple[Pattern, ...]:
        """Every pattern at the song's width, naming only the voices the file goes on to hold."""
        widened = [pattern.widened(channels) for pattern in patterns]
        return voiced_patterns(widened, slots=slots, repairs=self._repairs)

    def _voices(self) -> Voices:
        """The table this file's cells name positions in, as its own header says which kind it holds.

        A file switching instruments off plays its cells straight through the sample table, so that is
        what it comes back as. The instrument definitions such a file may still keep are what a tracker
        holds ready for the switch going back on, and a song playing samples sounds them nowhere.
        """
        samples = self._samples()
        if names_instruments(HeaderFlag(read_int(self._header, "flags"))):
            return InstrumentVoices(instruments=self._instruments(samples=len(samples)), samples=samples)

        held = len(self._instrument_offsets)
        if held:
            self._repairs.made(f"{held} instruments left aside by a song whose cells name samples", subject="song")

        return SampleVoices(samples=samples)

    @property
    def _body_start(self) -> int:
        """Where the first record the header points at sits, which the blocks before it stop at.

        A table entry of zero points at no record -- it is how this format states a pattern it stores
        nowhere -- so the first record is the nearest entry that names one.
        """
        pointed = (*self._instrument_offsets, *self._sample_offsets, *self._pattern_offsets)
        stored = tuple(offset for offset in pointed if offset != EMPTY_PATTERN_OFFSET)
        return min(stored, default=self._tables_end)

    def _header_at(self, offset: int, record: Record, *, subject: str) -> RecordValues:
        """The record one table entry names, read as an empty one where the file stops inside it.

        The zeroes a short file is read to the end of spell a record holding nothing, which keeps a
        song's numbering standing whatever the entry reached.
        """
        if offset + record.size > len(self._data):
            self._repairs.made(f"a record at {offset} of {len(self._data)} bytes held reads as empty", subject=subject)

        return record.unpack_at(self._data, offset)

    @property
    def _appended_start(self) -> int:
        """The byte past every record the header points at, where a writer's own blocks begin.

        Each kind of record states its own length -- an instrument and a sample header by their fixed
        size, a pattern and a compressed waveform by the count they open with -- so the furthest any of
        them reaches is where this format's own content ends.
        """
        reaches = [self._body_start]
        reaches += [offset + INSTRUMENT_HEADER_BYTES for offset in self._instrument_offsets]
        for offset in self._sample_offsets:
            values = SAMPLE_HEADER.unpack_at(self._data, offset)
            reaches += [offset + SAMPLE_HEADER_BYTES, stored_end(values, self._data)]

        for offset in self._stored_patterns:
            header = PATTERN_HEADER.unpack_at(self._data, offset)
            reaches.append(offset + PATTERN_HEADER_BYTES + read_int(header, "packed_size"))

        message_range = self._message_range()
        if message_range is not None:
            reaches.append(message_range[1])

        return max(reaches)

    def _message_range(self) -> tuple[int, int] | None:
        """The byte range the header's message occupies, or ``None`` when the file attaches none."""
        if not SpecialFlag.MESSAGE & read_int(self._header, "special"):
            return None

        offset = read_int(self._header, "message_offset")
        return offset, offset + read_int(self._header, "message_length")

    def _history(self) -> bytes:
        """The record of editing sessions a file carries, which its own switch says whether it holds."""
        if not SpecialFlag.HISTORY & read_int(self._header, "special"):
            return b""

        start = self._tables_end
        entries = int.from_bytes(self._data[start : start + HISTORY_COUNT_BYTES], "little")
        return self._data[start : start + HISTORY_COUNT_BYTES + HISTORY_ENTRY_BYTES * entries]

    def _extensions(self) -> Extensions:
        """Everything a writer put beside the records this format's own header points at.

        The stated blocks sit between the offset tables and the first record, and whatever a writer keeps
        for itself follows the last of them, so the two are found by where the header's own offsets stop.
        A later writer may also place the song message in this same gap, immediately before the first
        record, rather than after every record the way this library's own writer does -- so the message's
        own range is carved out of the region read for stated blocks wherever it falls inside it, or the
        message's own bytes would be misread as one.
        """
        history = self._history()
        start = self._tables_end + len(history)
        stop = self._body_start
        message_range = self._message_range()
        if message_range is not None and start <= message_range[0] < stop:
            stop = message_range[0]

        heading = self._data[start:stop]
        return Extensions(
            channel_names=block_names(heading, CHANNEL_NAMES_MAGIC, width=CHANNEL_NAME_BYTES),
            pattern_names=block_names(heading, PATTERN_NAMES_MAGIC, width=PATTERN_NAME_BYTES),
            history=history,
            appended=self._data[self._appended_start :],
        )

    def _message(self) -> str:
        """The free text the header points at, empty where the file attaches none.

        The header reserves a length for the block and the text inside it is terminated, so a reader
        stops at the terminator rather than at the length the writer reserved.
        """
        message_range = self._message_range()
        if message_range is None:
            return DEFAULT_MESSAGE

        start, stop = message_range
        return decode_text(self._data[start:stop])

    def _read_order(self, cursor: Cursor) -> OrderList:
        raw = cursor.take(read_int(self._header, "order_count"))
        return OrderList(entries=tuple(entry for entry in raw if entry not in (ORDER_SEPARATOR, ORDER_TERMINATOR)))

    def _read_table(self, cursor: Cursor, count_field: str) -> tuple[int, ...]:
        count = read_int(self._header, count_field)
        return struct.unpack(f"<{count}I", cursor.take(OFFSET_TABLE_ENTRY_BYTES * count))

    def _instruments(self, *, samples: int) -> tuple[Instrument, ...]:
        return tuple(
            routed_within(
                parse_instrument(
                    self._header_at(offset, INSTRUMENT_HEADER, subject=f"instrument {index}"),
                    subject=f"instrument {index}",
                    repairs=self._repairs,
                ),
                samples=samples,
                subject=f"instrument {index}",
                repairs=self._repairs,
            )
            for index, offset in enumerate(self._instrument_offsets)
        )

    def _samples(self) -> tuple[Sample, ...]:
        return tuple(
            read_sample(
                self._data,
                offset=offset,
                subject=f"sample {index}",
                repairs=self._repairs,
            )
            for index, offset in enumerate(self._sample_offsets)
        )

    @property
    def _stored_patterns(self) -> tuple[int, ...]:
        """Where each pattern the file actually stores begins."""
        return tuple(offset for offset in self._pattern_offsets if offset != EMPTY_PATTERN_OFFSET)

    def _patterns(self) -> tuple[Pattern, ...]:
        """Every pattern the order list can name, in the order the table numbers them."""
        return tuple(
            self._pattern_at(offset, subject=f"pattern {index}") for index, offset in enumerate(self._pattern_offsets)
        )

    def _pattern_at(self, offset: int, *, subject: str) -> Pattern:
        """The pattern stored at one offset, or the empty grid a slot with no block of its own holds.

        An entry of zero names a pattern the file stores nowhere, which a tracker plays as the default
        number of empty rows, so the slot is filled with those rather than read from the file's own
        opening bytes. An entry past the bytes the file holds names one just as absent, and is reported.
        """
        if offset == EMPTY_PATTERN_OFFSET:
            return Pattern.empty(rows=DEFAULT_ROWS, channels=MIN_CHANNELS)

        if offset > len(self._data):
            self._repairs.made(f"a block at {offset} of {len(self._data)} bytes held reads as silence", subject=subject)
            return Pattern.empty(rows=DEFAULT_ROWS, channels=MIN_CHANNELS)

        cursor = Cursor(self._data)
        cursor.seek(offset)
        return unpack_pattern(cursor, subject=subject, repairs=self._repairs)

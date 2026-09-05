from trackmod.binary.cursor import Cursor
from trackmod.binary.records.values import read_bytes, read_int
from trackmod.binary.text import decode_name
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.patterns.grid import Pattern
from trackmod.core.patterns.repair import voiced_patterns
from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.repair import repaired_order
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import InstrumentVoices
from trackmod.trackers.xm.instruments.parser import parse_instrument, parse_stub
from trackmod.trackers.xm.layout.file import FILE_HEADER
from trackmod.trackers.xm.layout.instrument import EMPTY_INSTRUMENT_HEADER, INSTRUMENT_HEADER
from trackmod.trackers.xm.patterns.parser import unpack_pattern
from trackmod.trackers.xm.samples.parser import read_samples
from trackmod.trackers.xm.settings import XMSettings
from trackmod.trackers.xm.spec.defaults import DEFAULT_SPEED
from trackmod.trackers.xm.spec.flags import HeaderFlag
from trackmod.trackers.xm.spec.identity import MAGIC
from trackmod.trackers.xm.spec.ranges import MIN_SPEED as DEFAULT_SPEED_FLOOR
from trackmod.trackers.xm.spec.sizes import (
    EMPTY_INSTRUMENT_HEADER_BYTES,
    FILE_HEADER_BYTES,
    HEADER_SIZE_OFFSET,
    INSTRUMENT_HEADER_BYTES,
)


class ModuleReader:
    """Walks a FastTracker 2 file, which stores no offset tables and is read strictly front to back."""

    def __init__(self, data: bytes) -> None:
        cursor = Cursor(data)
        self._repairs = Repairs()
        self._header = cursor.read(FILE_HEADER)
        if read_bytes(self._header, "magic") != MAGIC:
            raise ValueError("data does not open with the FastTracker 2 module tag")

        self._channels = read_int(self._header, "channels")
        self._order = self._read_order(data)
        cursor.seek(HEADER_SIZE_OFFSET + read_int(self._header, "header_size"))
        self._patterns = self._read_patterns(cursor)
        self._samples: list[Sample] = []
        self._instruments = self._read_instruments(cursor)

    def song(self) -> Song:
        """The format-agnostic content the file carries, with whatever it stated out of range drawn in."""
        voices = InstrumentVoices(instruments=self._instruments, samples=tuple(self._samples))
        song = Song(
            name=decode_name(read_bytes(self._header, "name")),
            channels=self._channels,
            patterns=voiced_patterns(self._patterns, slots=voices.slots, repairs=self._repairs),
            order=repaired_order(self._order, patterns=len(self._patterns), subject="song", repairs=self._repairs),
            voices=voices,
            playback=self._playback(),
        )
        self._repairs.warn()
        return song

    def settings(self) -> XMSettings:
        """The song-wide values this format adds, as the header states them."""
        return XMSettings(
            tracker=decode_name(read_bytes(self._header, "tracker")),
            flags=HeaderFlag(read_int(self._header, "flags")),
        )

    def _playback(self) -> Playback:
        """The clock the file starts on, with a speed of zero read as the one this format starts at."""
        speed = read_int(self._header, "speed")
        if speed < DEFAULT_SPEED_FLOOR:
            self._repairs.made(f"speed {speed} read as {DEFAULT_SPEED}", subject="song")
            speed = DEFAULT_SPEED

        return Playback(speed=speed, tempo=read_int(self._header, "tempo"))

    def _read_order(self, data: bytes) -> OrderList:
        """The played order list, whose restart position is pulled back inside it when a file overshoots."""
        count = read_int(self._header, "order_count")
        entries = tuple(data[FILE_HEADER_BYTES : FILE_HEADER_BYTES + count])
        restart = read_int(self._header, "restart_position")
        return OrderList(entries=entries, restart=min(restart, max(len(entries) - 1, 0)))

    def _read_patterns(self, cursor: Cursor) -> tuple[Pattern, ...]:
        count = read_int(self._header, "pattern_count")
        return tuple(
            unpack_pattern(cursor, channels=self._channels, subject=f"pattern {index}", repairs=self._repairs)
            for index in range(count)
        )

    def _read_instruments(self, cursor: Cursor) -> tuple[Instrument, ...]:
        """Every instrument the header counts, as far as the file goes on to hold them."""
        count = read_int(self._header, "instrument_count")
        instruments: list[Instrument] = []
        for index in range(count):
            if cursor.at_end:
                self._repairs.made(f"{count} instruments stated, {index} held", subject="song")
                break

            instruments.append(self._read_instrument(cursor, index=index))

        return tuple(instruments)

    def _read_instrument(self, cursor: Cursor, *, index: int) -> Instrument:
        identity = EMPTY_INSTRUMENT_HEADER.unpack(cursor.peek_padded(EMPTY_INSTRUMENT_HEADER_BYTES))
        size = read_int(identity, "header_size")
        length = read_int(identity, "sample_count")
        extended = length > 0 and size >= INSTRUMENT_HEADER_BYTES
        values = INSTRUMENT_HEADER.unpack(cursor.peek_padded(INSTRUMENT_HEADER_BYTES)) if extended else identity

        cursor.take_at_most(size)
        offset = len(self._samples)
        self._samples.extend(read_samples(cursor, count=length, subject=f"instrument {index}", repairs=self._repairs))
        if not extended:
            return parse_stub(values)

        return parse_instrument(
            values,
            offset=offset,
            length=length,
            subject=f"instrument {index}",
            repairs=self._repairs,
        )

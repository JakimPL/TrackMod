import struct

import numpy as np
import pytest

from tests.conftest import lattice
from tests.trackers.s3m.conftest import (
    REFERENCE_BYTE,
    REFERENCE_KEY,
    S3M_CHANNELS,
    cell_bytes,
    instrument_record,
    pattern_block,
    raw_module,
    silent_block,
)
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.keymap import pitched_keymap
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.grid import Pattern
from trackmod.core.repairs.report import RepairWarning
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import InstrumentVoices, SampleVoices
from trackmod.limits.compliance import Compliance
from trackmod.spec.grid import MIN_CHANNELS
from trackmod.spec.levels import CENTRE_PANNING, MAX_PANNING
from trackmod.spec.pitch import REFERENCE_RATE
from trackmod.trackers.s3m.layout.file import FILE_HEADER
from trackmod.trackers.s3m.layout.instrument import INSTRUMENT_RECORD
from trackmod.trackers.s3m.layout.pattern import PATTERN_HEADER
from trackmod.trackers.s3m.module import S3MModule
from trackmod.trackers.s3m.panning import shared_panning, stored_panning
from trackmod.trackers.s3m.patterns.sizing import block_bytes
from trackmod.trackers.s3m.settings import S3MSettings
from trackmod.trackers.s3m.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.s3m.spec.flags import (
    CHANNEL_RIGHT,
    CHANNEL_UNUSED,
    PANNING_STATED,
    PANNING_TABLE,
    STEREO_MIXING,
    HeaderFlag,
    RecordType,
)
from trackmod.trackers.s3m.spec.identity import MAGIC_MODULE, MAGIC_SAMPLE, UNSIGNED_FRAMES
from trackmod.trackers.s3m.spec.ranges import PATTERN_ROWS
from trackmod.trackers.s3m.spec.sizes import (
    CHANNELS_STORED,
    FILE_HEADER_BYTES,
    PARAGRAPH_BYTES,
    PARAPOINTER_BYTES,
)

ONE_ORDER = b"\x00"
UNREACHED_PARAGRAPH = 0xF000


def written(song: Song, settings: S3MSettings | None = None) -> bytes:
    return S3MModule.from_song(song, compliance=Compliance.CANONICAL, settings=settings).to_bytes()


def test_a_song_survives_being_written_and_read_back(s3m_song: Song) -> None:
    data = written(s3m_song)
    recovered = S3MModule.parse(data).song
    assert recovered.name == s3m_song.name
    assert recovered.channels == s3m_song.channels
    assert recovered.patterns == s3m_song.patterns
    assert recovered.order.entries == s3m_song.order.entries
    assert recovered.playback == s3m_song.playback
    assert [sample.name for sample in recovered.voices.samples] == [sample.name for sample in s3m_song.voices.samples]


def test_writing_a_module_read_back_states_the_same_bytes(s3m_song: Song) -> None:
    data = written(s3m_song)
    assert S3MModule.parse(data).to_bytes() == data


def test_the_size_model_agrees_with_the_written_file(s3m_song: Song) -> None:
    module = S3MModule.from_song(s3m_song, compliance=Compliance.CANONICAL)
    report = module.size()
    assert report.total == len(module.to_bytes())
    assert report.total == report.patterns + report.pcm + report.headers


def test_every_block_a_pointer_names_lands_on_the_block_it_claims(s3m_song: Song) -> None:
    # A pointer names the paragraph a block opens on rather than the byte it opens at, so following one
    # has to arrive at the block it claims: a record on its own tag, a pattern on the length it states.
    data = written(s3m_song)
    header = FILE_HEADER.unpack(data)
    orders, samples, patterns = (int(header[name]) for name in ("order_count", "sample_count", "pattern_count"))
    table = FILE_HEADER_BYTES + orders
    pointers = struct.unpack_from(f"<{samples + patterns}H", data, table)
    assert all(0 < pointer * PARAGRAPH_BYTES < len(data) for pointer in pointers)
    for pointer in pointers[:samples]:
        assert INSTRUMENT_RECORD.unpack_at(data, pointer * PARAGRAPH_BYTES)["magic"] == MAGIC_SAMPLE

    for pointer, pattern in zip(pointers[samples:], s3m_song.patterns):
        assert PATTERN_HEADER.unpack_at(data, pointer * PARAGRAPH_BYTES)["block_size"] == block_bytes(pattern)


def test_the_header_states_the_counts_and_the_clock_the_song_holds(s3m_song: Song) -> None:
    header = FILE_HEADER.unpack(written(s3m_song))
    assert header["magic"] == MAGIC_MODULE
    assert header["frame_format"] == UNSIGNED_FRAMES
    assert header["order_count"] == s3m_song.order.length
    assert header["sample_count"] == len(s3m_song.voices.samples)
    assert header["pattern_count"] == len(s3m_song.patterns)
    assert header["speed"] == DEFAULT_SPEED
    assert header["tempo"] == DEFAULT_TEMPO
    assert header["default_panning"] == 0


def test_the_settings_a_module_carries_survive_being_written_and_read_back(s3m_song: Song) -> None:
    centre = shared_panning(stored_panning(CENTRE_PANNING))
    settings = S3MSettings(
        global_volume=48,
        mix_volume=64,
        stereo=False,
        flags=HeaderFlag.AMIGA_LIMITS | HeaderFlag.ST3_VOLUME_SLIDES,
        channel_panning=(centre, 0, MAX_PANNING, centre) + (None,) * (CHANNELS_STORED - 4),
        created_with=0x1321,
    )
    recovered = S3MModule.parse(written(s3m_song, settings)).settings
    assert recovered.global_volume == settings.global_volume
    assert recovered.mix_volume == settings.mix_volume
    assert recovered.stereo == settings.stereo
    assert recovered.flags == settings.flags
    assert recovered.channel_panning == settings.channel_panning
    assert recovered.created_with == settings.created_with


def test_a_module_stating_no_panning_leaves_every_channel_on_its_own_side(s3m_song: Song) -> None:
    recovered = S3MModule.parse(written(s3m_song)).settings
    assert recovered.channel_panning is None


def test_a_channel_table_of_another_width_than_the_song_is_refused_where_it_is_bound(s3m_song: Song) -> None:
    # A module that reports itself writable and then refuses to serialise is a module a caller cannot
    # act on, so the disagreement is met where the two are put together.
    settings = S3MSettings(channels=tuple(range(8)) + (0xFF,) * (CHANNELS_STORED - 8))
    with pytest.raises(ValueError, match="8 channels"):
        S3MModule.from_song(s3m_song, compliance=Compliance.CANONICAL, settings=settings)


def test_a_file_whose_table_names_no_channel_reads_as_one_and_is_written_again() -> None:
    # A song holds a channel at the least, so the width is drawn up to one -- and the table that states
    # it is drawn up with it, which is what leaves the file writable rather than only readable.
    with pytest.warns(RepairWarning, match="settings table"):
        module = S3MModule.parse(raw_module(channels=0, patterns=(silent_block(),)))

    assert module.song.channels == MIN_CHANNELS
    assert module.violations() == ()
    assert S3MModule.parse(module.to_bytes()).song.channels == MIN_CHANNELS


def test_a_song_whose_cells_name_instruments_is_refused() -> None:
    sample = Sample(name="lead", pcm=lattice(np.linspace(-1.0, 1.0, 16)), rate=REFERENCE_RATE)
    builder = PatternBuilder(rows=PATTERN_ROWS, channels=1)
    builder.place(0, 0, Cell(note=REFERENCE_KEY, instrument=0))
    song = Song(
        name="voiced",
        channels=1,
        patterns=(builder.build(),),
        order=OrderList(entries=(0,)),
        voices=InstrumentVoices(
            instruments=(Instrument(name="lead", keymap=pitched_keymap(sample=0)),),
            samples=(sample,),
        ),
        playback=Playback(speed=DEFAULT_SPEED, tempo=DEFAULT_TEMPO),
    )
    with pytest.raises(ValueError, match="flatten its voices"):
        S3MModule.from_song(song, compliance=Compliance.CANONICAL)


def test_data_opening_with_another_tag_is_refused() -> None:
    with pytest.raises(ValueError, match="Scream Tracker 3 module tag"):
        S3MModule.parse(raw_module(magic=b"XXXX"))


def test_an_order_marker_names_no_position_a_song_plays() -> None:
    data = raw_module(
        orders=bytes((0, 0xFE, 0, 0xFF)),
        records=(instrument_record(kind=int(RecordType.EMPTY)),),
        patterns=(silent_block(),),
    )
    assert S3MModule.parse(data).song.order.entries == (0, 0)


def test_a_pattern_the_file_stores_nowhere_plays_a_whole_empty_one() -> None:
    data = raw_module(
        orders=b"\x00\x01",
        records=(instrument_record(kind=int(RecordType.EMPTY)),),
        patterns=(silent_block(), None),
    )
    song = S3MModule.parse(data).song
    assert len(song.patterns) == 2
    assert song.patterns[1] == Pattern.empty(rows=PATTERN_ROWS, channels=song.channels)


def test_a_file_states_its_width_in_the_channel_settings() -> None:
    data = raw_module(
        channels=S3M_CHANNELS,
        records=(instrument_record(kind=int(RecordType.EMPTY)),),
        patterns=(pattern_block((cell_bytes(0, note=REFERENCE_BYTE, sample=1),)),),
    )
    song = S3MModule.parse(data).song
    assert song.channels == S3M_CHANNELS
    assert song.patterns[0].cell(0, 0) == Cell(note=Note(60), instrument=0)


def test_a_module_saves_under_its_own_extension(tmp_path, s3m_song: Song) -> None:
    module = S3MModule.from_song(s3m_song, compliance=Compliance.CANONICAL)
    path = tmp_path / f"song{module.extension}"
    module.save(path)
    assert module.extension == ".s3m"
    assert S3MModule.load(path).song.name == s3m_song.name


def test_a_panning_slot_claiming_nothing_reads_as_a_channel_stating_none() -> None:
    data = raw_module(
        records=(instrument_record(kind=int(RecordType.EMPTY)),),
        patterns=(silent_block(),),
        panning=bytes((PANNING_STATED | 7, 0)),
    )
    panning = S3MModule.parse(data).settings.channel_panning
    assert panning is not None
    assert panning[0] == 119
    assert panning[1] is None


def test_a_position_between_the_sixteen_a_channel_states_lands_on_the_nearest_of_them(s3m_song: Song) -> None:
    settings = S3MSettings(channel_panning=(CENTRE_PANNING,) + (None,) * (CHANNELS_STORED - 1))
    assert FILE_HEADER.unpack(written(s3m_song, settings))["default_panning"] == PANNING_TABLE
    recovered = S3MModule.parse(written(s3m_song, settings)).settings.channel_panning
    assert recovered is not None
    assert recovered[0] == shared_panning(stored_panning(CENTRE_PANNING))


def test_a_clock_below_the_floor_the_format_starts_at_reads_as_the_one_it_starts_on() -> None:
    data = raw_module(
        speed=0,
        tempo=8,
        records=(instrument_record(kind=int(RecordType.EMPTY)),),
        patterns=(silent_block(),),
    )
    with pytest.warns(UserWarning, match="drawn into range"):
        song = S3MModule.parse(data).song

    assert song.playback == Playback(speed=DEFAULT_SPEED, tempo=DEFAULT_TEMPO)


def test_a_panning_block_the_file_stops_inside_leaves_every_channel_stating_none() -> None:
    data = raw_module(orders=b"", panning=bytes((PANNING_STATED | 7,)))
    truncated = data[: FILE_HEADER_BYTES + 4]
    assert S3MModule.parse(truncated).settings.channel_panning is None


def test_a_pattern_playing_nothing_states_no_key_at_all() -> None:
    data = raw_module(
        records=(instrument_record(kind=int(RecordType.EMPTY)),),
        patterns=(silent_block(),),
    )
    module = S3MModule.parse(data)
    assert module.violations() == ()
    assert module.exceeded() == ()


def test_the_positions_past_an_end_of_song_marker_are_music_the_order_still_names() -> None:
    # Composers of this lineage kept a spare section after the marker that ends the piece, which a
    # player sounds as a song of its own. The order list holds one sequence, so every position the
    # table names is kept and none of that music is dropped.
    data = raw_module(
        orders=bytes((0, 0xFF, 1, 0xFF)),
        records=(instrument_record(kind=int(RecordType.EMPTY)),),
        patterns=(silent_block(), silent_block()),
    )
    assert S3MModule.parse(data).song.order.entries == (0, 1)


def test_a_cell_on_a_channel_above_a_gap_in_the_settings_table_is_music() -> None:
    # A packed cell names its channel by the slot it takes in the settings table, so a table naming
    # slots 0 and 2 states three channels and the cell on the third is sounded.
    data = bytearray(
        raw_module(
            records=(instrument_record(kind=int(RecordType.EMPTY)),),
            patterns=(pattern_block((cell_bytes(2, note=REFERENCE_BYTE, sample=1),)),),
        )
    )
    settings = bytearray([CHANNEL_UNUSED] * CHANNELS_STORED)
    settings[0], settings[2] = 0, CHANNEL_RIGHT
    data[64:96] = settings
    song = S3MModule.parse(bytes(data)).song
    assert song.channels == 3
    assert song.patterns[0].cell(row=0, channel=2).note == REFERENCE_KEY


def pointed_past_the_file(*, pointer: int) -> bytes:
    """A module of one record and one pattern whose ``pointer``-th table entry names no byte it holds."""
    data = bytearray(
        raw_module(
            orders=ONE_ORDER,
            records=(instrument_record(length=4, kind=int(RecordType.SAMPLE)),),
            patterns=(silent_block(),),
            waveforms=(bytes(4),),
        )
    )
    table = FILE_HEADER_BYTES + len(ONE_ORDER) + PARAPOINTER_BYTES * pointer
    struct.pack_into("<H", data, table, UNREACHED_PARAGRAPH)
    return bytes(data)


def test_a_block_pointer_past_the_bytes_the_file_holds_reads_as_silence() -> None:
    with pytest.warns(RepairWarning, match="reads as silence"):
        song = S3MModule.parse(pointed_past_the_file(pointer=1)).song

    assert song.patterns[0] == Pattern.empty(rows=PATTERN_ROWS, channels=song.channels)


def test_a_record_pointer_past_the_bytes_the_file_holds_reads_as_an_empty_slot() -> None:
    # A slot standing empty keeps a song's sample numbering, which is what every cell naming a sample
    # counts against, so a pointer reaching nothing leaves the numbering where it was.
    with pytest.warns(RepairWarning, match="reads as empty"):
        song = S3MModule.parse(pointed_past_the_file(pointer=0)).song

    assert len(song.voices.samples) == 1
    assert song.voices.samples[0].frames == 0


def test_a_file_stopping_inside_a_block_reads_its_rows_as_far_as_they_go() -> None:
    data = raw_module(
        orders=ONE_ORDER,
        records=(instrument_record(kind=int(RecordType.EMPTY)),),
        patterns=(pattern_block((cell_bytes(0, note=REFERENCE_BYTE, sample=1),)),),
    )
    table = FILE_HEADER_BYTES + len(ONE_ORDER) + PARAPOINTER_BYTES
    (paragraph,) = struct.unpack_from("<H", data, table)

    with pytest.warns(RepairWarning, match="rows past the end of the stream"):
        song = S3MModule.parse(data[: paragraph * PARAGRAPH_BYTES + 1]).song

    assert song.patterns[0] == Pattern.empty(rows=PATTERN_ROWS, channels=song.channels)


def test_the_song_wide_values_a_hand_built_header_states_are_read_back_from_it() -> None:
    # Every value here sits in a byte of its own in the file header, and the mixing byte carries two of
    # them at once: the volume in its low seven bits and whether the tracker mixed in stereo in the top.
    data = raw_module(
        name=b"handmade",
        global_volume=48,
        mix_volume=STEREO_MIXING | 0x30,
        flags=int(HeaderFlag.AMIGA_LIMITS),
        created_with=0x1321,
        records=(instrument_record(kind=int(RecordType.EMPTY)),),
        patterns=(silent_block(),),
    )
    module = S3MModule.parse(data)

    assert module.song.name == "handmade"
    assert module.settings.global_volume == 48
    assert module.settings.mix_volume == 0x30
    assert module.settings.stereo
    assert module.settings.flags is HeaderFlag.AMIGA_LIMITS
    assert module.settings.created_with == 0x1321


def test_a_hand_built_file_carrying_frames_reads_them_back_as_the_waveform_they_are() -> None:
    # The whole read path in one file: a record naming its waveform by the paragraph it opens on, a
    # length in frames, and the bytes themselves. Frames are stored unsigned, so the middle of the byte
    # is silence and either end is full scale.
    waveform = bytes((0x80, 0xC0, 0x40, 0x00, 0xFF, 0xA0, 0x60, 0x80))
    sounded = [0.0, 0.5, -0.5, -1.0, 127 / 128, 0.25, -0.25, 0.0]
    data = raw_module(
        orders=ONE_ORDER,
        records=(instrument_record(name=b"lead", length=len(waveform), volume=48, c2spd=22050),),
        patterns=(silent_block(),),
        waveforms=(waveform,),
    )

    (sample,) = S3MModule.parse(data).song.voices.samples
    assert sample.name == "lead"
    assert sample.rate == 22050
    assert sample.volume == 48
    assert sample.frames == len(waveform)
    assert np.array_equal(sample.pcm, np.array(sounded))


SAMPLE_SHAPES = (
    Sample(name="stereo", pcm=lattice(np.stack([np.linspace(-1.0, 1.0, 12)] * 2, axis=1)), rate=REFERENCE_RATE),
    Sample(
        name="eight",
        pcm=lattice(np.linspace(-1.0, 1.0, 12), BitDepth.EIGHT),
        rate=REFERENCE_RATE,
        depth=BitDepth.EIGHT,
    ),
    Sample(name="empty", pcm=np.zeros(0), rate=REFERENCE_RATE),
    Sample(name="single", pcm=lattice(np.zeros(1)), rate=REFERENCE_RATE),
)


@pytest.mark.parametrize("sample", SAMPLE_SHAPES, ids=[sample.name for sample in SAMPLE_SHAPES])
def test_a_waveform_of_any_shape_this_format_stores_survives_the_whole_module(
    sample: Sample,
    s3m_song: Song,
) -> None:
    # Each of these takes a different path through the record: two channel blocks against one, a byte a
    # frame against two, and the two lengths that leave a record pointing at nothing to read.
    song = s3m_song.model_copy(
        update={
            "patterns": (Pattern.empty(rows=PATTERN_ROWS, channels=S3M_CHANNELS),),
            "order": OrderList(entries=(0,)),
            "voices": SampleVoices(samples=(sample,)),
        }
    )
    module = S3MModule.from_song(song, compliance=Compliance.CANONICAL)
    assert module.violations() == ()
    assert module.size().total == len(module.to_bytes())

    (recovered,) = S3MModule.parse(module.to_bytes()).song.voices.samples
    assert (recovered.frames, recovered.channels, recovered.depth) == (sample.frames, sample.channels, sample.depth)
    assert np.array_equal(recovered.pcm, sample.pcm)

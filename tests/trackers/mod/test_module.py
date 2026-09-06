import numpy as np
import pytest

from tests.conftest import lattice
from tests.trackers.mod.conftest import (
    cell_bytes,
    mod_pattern,
    raw_module,
    sample_record,
    silent_pattern,
)
from trackmod.core.repairs.report import RepairWarning
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import SampleVoices
from trackmod.limits.compliance import Compliance
from trackmod.spec.pitch import RATE_NOTE, REFERENCE_RATE
from trackmod.trackers.amiga.note import PERIODS
from trackmod.trackers.amiga.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.amiga.spec.ranges import MAX_ORDERS, PATTERN_ROWS
from trackmod.trackers.amiga.spec.sizes import ORDER_TABLE_BYTES, SAMPLE_TABLE_OFFSET
from trackmod.trackers.mod.dialect import DIALECTS
from trackmod.trackers.mod.layout.file import SEQUENCE
from trackmod.trackers.mod.module import MODModule
from trackmod.trackers.mod.settings import MODSettings
from trackmod.trackers.mod.spec.identity import TAG_BYTES, TAG_OFFSET
from trackmod.trackers.mod.spec.ranges import CANONICAL_CHANNELS, TAGGED_MAX_PATTERNS
from trackmod.trackers.mod.spec.sizes import FILE_HEADER_BYTES, SAMPLE_TABLE_BYTES

ODD_FRAMES = 25


def rewritten(song: Song, settings: MODSettings | None = None) -> MODModule:
    """The module a song is written to and read back from, which is what a round trip has to preserve."""
    data = MODModule.from_song(song, compliance=Compliance.CANONICAL, settings=settings).to_bytes()
    return MODModule.parse(data)


def test_a_song_reads_back_as_it_was_written(mod_song: Song) -> None:
    recovered = rewritten(mod_song).song
    assert recovered.name == mod_song.name
    assert recovered.channels == mod_song.channels
    assert recovered.patterns == mod_song.patterns
    assert recovered.order == mod_song.order
    assert recovered.voices == mod_song.voices
    assert recovered.playback == mod_song.playback


def test_a_file_reads_back_byte_for_byte(mod_song: Song) -> None:
    data = MODModule.from_song(mod_song, compliance=Compliance.CANONICAL).to_bytes()
    assert MODModule.parse(data).to_bytes() == data


def test_the_size_model_agrees_with_the_written_file(mod_song: Song) -> None:
    module = MODModule.from_song(mod_song, compliance=Compliance.CANONICAL)
    assert module.size().total == len(module.to_bytes())
    assert module.size().headers == FILE_HEADER_BYTES


def test_a_module_is_tagged_by_the_width_and_the_patterns_it_holds(mod_song: Song) -> None:
    data = MODModule.from_song(mod_song, compliance=Compliance.CANONICAL).to_bytes()
    assert data[TAG_OFFSET : TAG_OFFSET + TAG_BYTES] == b"M.K."

    wide = mod_song.model_copy(
        update={
            "channels": 6,
            "patterns": tuple(pattern.widened(6) for pattern in mod_song.patterns),
        }
    )
    written = MODModule.from_song(wide, compliance=Compliance.EXTENDED).to_bytes()
    assert written[TAG_OFFSET : TAG_OFFSET + TAG_BYTES] == b"6CHN"


def test_a_song_holding_more_patterns_than_the_plain_tag_was_read_with_states_the_other_one(
    mod_song: Song,
) -> None:
    many = mod_song.model_copy(
        update={
            "patterns": tuple(mod_song.patterns[0] for _ in range(TAGGED_MAX_PATTERNS + 1)),
            "order": OrderList(entries=(0,)),
        }
    )
    data = MODModule.from_song(many, compliance=Compliance.EXTENDED).to_bytes()
    assert data[TAG_OFFSET : TAG_OFFSET + TAG_BYTES] == b"M!K!"


def test_the_tag_a_file_carried_is_the_tag_it_is_written_back_under(mod_song: Song) -> None:
    stated = MODSettings(dialect=DIALECTS[b"M!K!"])
    data = MODModule.from_song(mod_song, compliance=Compliance.CANONICAL, settings=stated).to_bytes()
    assert data[TAG_OFFSET : TAG_OFFSET + TAG_BYTES] == b"M!K!"
    assert MODModule.parse(data).settings.dialect == DIALECTS[b"M!K!"]


def test_a_tag_stating_another_width_than_the_song_holds_is_refused_where_it_is_bound(mod_song: Song) -> None:
    # A module that reports itself writable and then refuses to serialise is a module a caller cannot
    # act on, so the disagreement is met where the two are put together.
    stated = MODSettings(dialect=DIALECTS[b"6CHN"])
    with pytest.raises(ValueError, match="states 6 channels"):
        MODModule.from_song(mod_song, compliance=Compliance.CANONICAL, settings=stated)


def test_the_clock_is_the_one_every_module_of_this_format_starts_on(mod_song: Song) -> None:
    assert rewritten(mod_song).song.playback == Playback(speed=DEFAULT_SPEED, tempo=DEFAULT_TEMPO)

    hurried = mod_song.model_copy(update={"playback": Playback(speed=3, tempo=140)})
    reported = MODModule.from_song(hurried, compliance=Compliance.EXTENDED).violations()
    assert {violation.capability.value for violation in reported} == {"speed", "tempo"}


def test_a_song_whose_cells_name_instruments_is_refused(song: Song) -> None:
    with pytest.raises(ValueError, match="name samples"):
        MODModule.from_song(song, compliance=Compliance.CANONICAL)


def test_an_order_longer_than_its_table_is_drawn_back_inside_it() -> None:
    data = raw_module(order_count=MAX_ORDERS + 1, orders=bytes(MAX_ORDERS), patterns=silent_pattern())
    with pytest.warns(RepairWarning, match=f"read as the {MAX_ORDERS}"):
        song = MODModule.parse(data).song

    assert song.order.length == MAX_ORDERS


def test_a_restart_past_the_order_is_drawn_back_onto_it() -> None:
    data = raw_module(order_count=2, restart=127, orders=bytes(2), patterns=silent_pattern())
    assert MODModule.parse(data).song.order.restart == 1


def test_a_pattern_the_order_never_reaches_is_kept() -> None:
    # The order names the highest pattern a song plays, and the file may hold more than it plays — the
    # length left over is what says so, and the waveforms are found by reading past all of them.
    data = raw_module(
        order_count=1,
        orders=bytes(1),
        patterns=silent_pattern() * 3,
        waveforms=b"",
    )
    song = MODModule.parse(data).song
    assert len(song.patterns) == 3


def test_a_file_stopping_inside_its_patterns_reads_the_rest_as_silence() -> None:
    data = raw_module(order_count=1, orders=bytes(1), patterns=silent_pattern()[:64])
    with pytest.warns(RepairWarning, match="read as silence"):
        song = MODModule.parse(data).song

    assert song.patterns[0].rows == PATTERN_ROWS


def test_the_slots_a_song_keeps_run_up_to_the_last_one_it_uses() -> None:
    # A file writes thirty-one records whatever it fills. Only the slots a cell can reach come back, and
    # an unfilled slot before a filled one stays, because the cells number their samples by position.
    records = (
        sample_record(name=b"first", length=4, volume=64),
        sample_record(),
        sample_record(name=b"third", length=4, volume=64),
    )
    data = raw_module(
        records=records,
        order_count=1,
        orders=bytes(1),
        patterns=silent_pattern(),
        waveforms=bytes(16),
    )
    samples = MODModule.parse(data).song.voices.samples
    assert [sample.name for sample in samples] == ["first", "", "third"]


def test_a_slot_a_cell_names_is_kept_even_with_no_waveform_in_it() -> None:
    played = cell_bytes(period=PERIODS[RATE_NOTE], sample=5)
    data = raw_module(
        records=(sample_record(name=b"first", length=4, volume=64),),
        order_count=1,
        orders=bytes(1),
        patterns=played + silent_pattern()[len(played) :],
        waveforms=bytes(8),
    )
    song = MODModule.parse(data).song
    assert song.voices.slots == 5
    assert song.patterns[0].cell(0, 0).instrument == 4


def test_a_module_saves_and_loads_under_its_own_extension(tmp_path, mod_song: Song) -> None:
    module = MODModule.from_song(mod_song, compliance=Compliance.CANONICAL)
    path = tmp_path / f"song{module.extension}"
    module.save(path)
    assert MODModule.load(path).song.name == mod_song.name


def test_a_song_wider_than_its_tracker_read_is_reported_rather_than_refused(mod_song: Song) -> None:
    wide = mod_song.model_copy(
        update={
            "channels": 8,
            "patterns": tuple(pattern.widened(8) for pattern in mod_song.patterns),
        }
    )
    assert MODModule.from_song(wide, compliance=Compliance.EXTENDED).violations() == ()
    assert MODModule.from_song(wide, compliance=Compliance.CANONICAL).violations() != ()


def test_a_song_of_one_sample_and_no_patterns_still_writes_the_whole_header() -> None:
    lone = Song(
        name="lone",
        channels=CANONICAL_CHANNELS,
        patterns=(mod_pattern(channels=CANONICAL_CHANNELS, samples=1, seed=1),),
        order=OrderList(entries=(0,)),
        voices=SampleVoices(
            samples=(
                Sample(
                    name="one",
                    pcm=lattice(np.linspace(-1.0, 1.0, 8), BitDepth.EIGHT),
                    rate=REFERENCE_RATE,
                    depth=BitDepth.EIGHT,
                ),
            )
        ),
        playback=Playback(speed=DEFAULT_SPEED, tempo=DEFAULT_TEMPO),
    )
    module = MODModule.from_song(lone, compliance=Compliance.CANONICAL)
    assert module.violations() == ()
    assert len(module.to_bytes()) == module.size().total


def test_the_restart_byte_a_file_held_is_written_back_as_it_stood() -> None:
    # Trackers of this lineage write a marker here rather than a position, so the order list holds the
    # position it can and the byte itself is kept beside it — otherwise every such file would come back
    # a byte different from the one it went in as.
    data = raw_module(order_count=2, restart=127, orders=bytes(2), patterns=silent_pattern())
    module = MODModule.parse(data)
    assert module.settings.restart == 127
    assert module.song.order.restart == 1
    assert module.to_bytes() == data


def test_a_song_built_from_nothing_states_the_position_its_order_holds(mod_song: Song) -> None:
    data = MODModule.from_song(mod_song, compliance=Compliance.CANONICAL).to_bytes()
    sequence = SEQUENCE.unpack_at(data, SAMPLE_TABLE_OFFSET + SAMPLE_TABLE_BYTES)
    assert sequence["restart"] == mod_song.order.restart


def test_a_slot_carrying_only_a_name_is_kept_for_the_text_it_holds() -> None:
    # Trackers of this lineage wrote liner notes into the sample names, so a named slot holding no
    # waveform still carries something the file states rather than padding a reader may drop.
    records = (
        sample_record(name=b"first", length=4, volume=64),
        sample_record(name=b"-- greetings --"),
    )
    data = raw_module(
        records=records,
        order_count=1,
        orders=bytes(1),
        patterns=silent_pattern(),
        waveforms=bytes(8),
    )
    samples = MODModule.parse(data).song.voices.samples
    assert [sample.name for sample in samples] == ["first", "-- greetings --"]
    assert samples[1].frames == 0


def test_a_stale_entry_past_the_positions_a_song_plays_names_no_pattern() -> None:
    # Shortening a song leaves the table as it stood, so an entry past the count names a pattern the
    # file never stored. Reading it would take the waveforms for music.
    orders = bytearray(ORDER_TABLE_BYTES)
    orders[60] = 5
    data = raw_module(
        records=(sample_record(name=b"kept", length=4, volume=64),),
        order_count=1,
        orders=bytes(orders),
        patterns=silent_pattern(),
        waveforms=bytes(8),
    )
    module = MODModule.parse(data)
    assert len(module.song.patterns) == 1
    assert module.song.voices.samples[0].frames == 8


def test_a_song_holding_no_patterns_keeps_the_waveforms_it_carries(mod_samples: tuple[Sample, ...]) -> None:
    # An unplayed order table is all zeroes, which names position 0 as surely as a played one does. The
    # room the file leaves is what says no pattern was stored there.
    silent = Song(
        name="quiet",
        channels=CANONICAL_CHANNELS,
        patterns=(),
        order=OrderList(entries=()),
        voices=SampleVoices(samples=mod_samples[:1]),
        playback=Playback(speed=DEFAULT_SPEED, tempo=DEFAULT_TEMPO),
    )
    data = MODModule.from_song(silent, compliance=Compliance.CANONICAL).to_bytes()
    module = MODModule.parse(data)
    assert module.song.patterns == ()
    assert module.song.voices.samples[0].pcm.tolist() == mod_samples[0].pcm.tolist()
    assert module.to_bytes() == data


def test_an_order_naming_more_patterns_than_the_file_holds_reads_the_ones_it_holds() -> None:
    data = raw_module(order_count=2, orders=bytes((0, 3)), patterns=silent_pattern())
    with pytest.warns(RepairWarning, match="an order naming 4 patterns read as the 1 the file holds"):
        song = MODModule.parse(data).song

    assert len(song.patterns) == 1


def test_a_waveform_of_an_odd_length_is_closed_by_the_frame_that_fills_its_pair(
    mod_song: Song,
    mod_samples: tuple[Sample, ...],
) -> None:
    # A record counts a waveform in pairs of frames, so an odd one is stored with a silent frame after
    # it. The size model charges for that frame, the file holds it, and the length the record states is
    # what a reader gets back.
    odd = Sample(
        name="odd",
        pcm=lattice(np.linspace(-1.0, 1.0, ODD_FRAMES), BitDepth.EIGHT),
        rate=REFERENCE_RATE,
        depth=BitDepth.EIGHT,
    )
    song = mod_song.model_copy(update={"voices": SampleVoices(samples=mod_samples + (odd,))})
    module = MODModule.from_song(song, compliance=Compliance.CANONICAL)

    assert module.violations() == ()
    assert module.size().total == len(module.to_bytes())

    recovered = MODModule.parse(module.to_bytes()).song.voices.samples[-1]
    assert recovered.frames == ODD_FRAMES + 1
    assert np.array_equal(recovered.pcm[:ODD_FRAMES], odd.pcm)
    assert recovered.pcm[-1] == 0.0

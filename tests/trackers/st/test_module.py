from pathlib import Path

import pytest

from tests.trackers.amiga.conftest import cell_bytes, sample_record, silent_pattern
from tests.trackers.st.conftest import raw_module
from trackmod.core.repairs.report import RepairWarning
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.song import Song
from trackmod.limits.compliance import Compliance
from trackmod.trackers.amiga.note import PERIODS
from trackmod.trackers.amiga.spec.ranges import MAX_ORDERS
from trackmod.trackers.st.module import STModule
from trackmod.trackers.st.spec.defaults import DEFAULT_TEMPO_BYTE
from trackmod.trackers.st.spec.ranges import CHANNELS
from trackmod.trackers.st.spec.sizes import FILE_HEADER_BYTES, SAMPLE_SLOTS

STATED_TEMPO = 96
LOOPED_SLOT = 2


def written(song: Song) -> bytes:
    return STModule.from_song(song, compliance=Compliance.CANONICAL).to_bytes()


def test_the_header_this_format_writes_is_six_hundred_bytes(st_song: Song) -> None:
    assert FILE_HEADER_BYTES == 600
    assert SAMPLE_SLOTS == 15
    assert written(st_song)[:20] == b"trackmod" + bytes(12)


def test_a_song_reads_back_as_it_was_written(st_song: Song) -> None:
    recovered = STModule.parse(written(st_song))
    assert recovered.song.patterns == st_song.patterns
    assert recovered.song.order.entries == st_song.order.entries
    assert recovered.song.playback == st_song.playback
    assert recovered.song.name == st_song.name


def test_a_module_written_twice_reaches_the_same_bytes(st_song: Song) -> None:
    once = written(st_song)
    assert STModule.parse(once).to_bytes() == once


def test_every_waveform_survives_the_round_trip(st_song: Song) -> None:
    recovered = STModule.parse(written(st_song))
    for before, after in zip(st_song.voices.samples, recovered.song.voices.samples):
        assert after.pcm.tolist() == before.pcm.tolist()
        assert after.name == before.name
        assert after.volume == before.volume


def test_a_loop_offset_is_counted_in_the_bytes_this_format_states_it_in(st_song: Song) -> None:
    # Amiga ProTracker counts this field in words, and the trackers that wrote this layout counted it in
    # bytes, so the same loop is stored as two different numbers by the two formats.
    looped = st_song.voices.samples[LOOPED_SLOT]
    assert looped.loop is not None
    record = written(st_song)[20 + LOOPED_SLOT * 30 : 20 + LOOPED_SLOT * 30 + 30]
    assert int.from_bytes(record[26:28], "big") == looped.loop.begin

    recovered = STModule.parse(written(st_song)).song.voices.samples[LOOPED_SLOT].loop
    assert recovered is not None
    assert recovered.begin == looped.loop.begin


def test_the_byte_the_header_held_is_written_back_as_it_stood() -> None:
    data = raw_module(order_count=1, tempo=STATED_TEMPO, patterns=silent_pattern(channels=CHANNELS))
    module = STModule.parse(data)
    assert module.settings.tempo == STATED_TEMPO
    assert module.to_bytes()[FILE_HEADER_BYTES - 129] == STATED_TEMPO


def test_a_song_built_from_nothing_states_the_byte_every_module_opens_on(st_song: Song) -> None:
    assert written(st_song)[FILE_HEADER_BYTES - 129] == DEFAULT_TEMPO_BYTE


def test_a_song_resuming_past_its_first_position_is_refused(st_song: Song) -> None:
    resuming = st_song.model_copy(update={"order": OrderList(entries=(0, 1, 0), restart=1)})
    with pytest.raises(ValueError, match="states no restart"):
        written(resuming)


def test_an_order_longer_than_its_table_reads_as_the_table() -> None:
    data = raw_module(
        order_count=MAX_ORDERS + 1,
        orders=bytes(MAX_ORDERS),
        patterns=silent_pattern(channels=CHANNELS),
    )
    with pytest.warns(RepairWarning, match=f"read as the {MAX_ORDERS}"):
        module = STModule.parse(data)

    assert module.song.order.length == MAX_ORDERS


def test_a_file_stopping_inside_a_pattern_gives_up_the_music_it_holds() -> None:
    data = raw_module(order_count=1, patterns=silent_pattern(channels=CHANNELS)[:64])
    with pytest.warns(RepairWarning, match="read as silence"):
        module = STModule.parse(data)

    assert len(module.song.patterns) == 1


def test_the_slots_a_song_keeps_run_up_to_the_last_one_it_uses() -> None:
    played = cell_bytes(period=PERIODS[60], sample=4)
    data = raw_module(
        order_count=1,
        records=(sample_record(name=b"first", length=2),),
        patterns=played + silent_pattern(channels=CHANNELS)[len(played) :],
        waveforms=bytes(4),
    )
    assert len(STModule.parse(data).song.voices.samples) == 4


def test_a_cell_naming_a_slot_past_the_fifteen_this_format_holds_carries_its_channel_on() -> None:
    # The cell splits its sample number across two nibbles, so a file can name more slots than the
    # fifteen records behind it, which is the shape a ProTracker module read here would take.
    played = cell_bytes(period=PERIODS[60], sample=20)
    data = raw_module(
        order_count=1,
        patterns=played + silent_pattern(channels=CHANNELS)[len(played) :],
    )
    with pytest.warns(RepairWarning, match="past the 15 held"):
        STModule.parse(data)


def test_an_order_naming_more_patterns_than_the_file_holds_reads_the_ones_it_holds() -> None:
    data = raw_module(order_count=2, orders=bytes((0, 3)), patterns=silent_pattern(channels=CHANNELS))
    with pytest.warns(RepairWarning, match="read as the 1 the file holds"):
        module = STModule.parse(data)

    assert len(module.song.patterns) == 1


def test_a_module_reads_back_from_the_file_it_was_saved_to(tmp_path: Path, st_song: Song) -> None:
    path = tmp_path / "song.mod"
    STModule.from_song(st_song, compliance=Compliance.CANONICAL).save(path)
    assert STModule.load(path).song.patterns == st_song.patterns

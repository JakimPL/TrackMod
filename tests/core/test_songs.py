import numpy as np
import pytest

from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.keymap import pitched_keymap
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.grid import Pattern
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import (
    InstrumentVoices,
    SampleVoices,
    Voices,
)

RATE = 44100


ATOM = Sample(name="atom", pcm=np.zeros(8), rate=RATE)
LEAD = InstrumentVoices(instruments=(Instrument(name="lead", keymap=pitched_keymap(sample=0)),), samples=(ATOM,))


def make_song(
    *,
    channels: int = 2,
    patterns: tuple[Pattern, ...] = (),
    order: OrderList | None = None,
    voices: Voices | None = None,
) -> Song:
    """A minimal valid song, with one part swapped out per test."""
    grids = patterns or (Pattern.empty(rows=4, channels=channels),)
    return Song(
        name="song",
        channels=channels,
        patterns=grids,
        order=OrderList.sequential(len(grids)) if order is None else order,
        voices=LEAD if voices is None else voices,
        playback=Playback(speed=6, tempo=125),
    )


def naming(voice: int) -> Pattern:
    """A one-cell grid whose instrument column names one voice."""
    builder = PatternBuilder(rows=4, channels=2)
    builder.place(0, 0, Cell(note=Note(60), instrument=voice))
    return builder.build()


def test_a_song_reports_the_rows_its_order_plays() -> None:
    patterns = (Pattern.empty(rows=4, channels=2), Pattern.empty(rows=6, channels=2))
    assert make_song(patterns=patterns, order=OrderList(entries=(0, 1, 0))).rows == 14


def test_a_pattern_of_the_wrong_width_is_rejected() -> None:
    with pytest.raises(ValueError):
        make_song(patterns=(Pattern.empty(rows=4, channels=3),))


def test_an_order_naming_a_missing_pattern_is_rejected() -> None:
    with pytest.raises(ValueError):
        make_song(order=OrderList(entries=(0, 1)))


def test_an_instrument_naming_a_missing_sample_is_rejected() -> None:
    with pytest.raises(ValueError):
        InstrumentVoices(instruments=(Instrument(name="lead", keymap=pitched_keymap(sample=4)),), samples=(ATOM,))


def test_a_cell_naming_a_voice_the_song_leaves_out_is_rejected() -> None:
    with pytest.raises(ValueError, match="names voice 1 of 1"):
        make_song(patterns=(naming(1),))


def test_a_song_whose_cells_name_samples_holds_a_sample_table() -> None:
    voices = SampleVoices(samples=(ATOM, ATOM))
    song = make_song(patterns=(naming(1),), voices=voices)
    assert song.voices is voices
    assert song.voices.slots == 2


def test_a_table_of_instruments_is_as_wide_as_the_instruments_it_holds() -> None:
    assert LEAD.slots == 1
    assert len(LEAD.samples) == 1


def test_a_song_needs_at_least_one_channel() -> None:
    with pytest.raises(ValueError):
        make_song(channels=0)


def test_a_restart_position_outside_the_order_is_rejected() -> None:
    with pytest.raises(ValueError):
        OrderList(entries=(0, 1), restart=2)


def test_a_sequential_order_plays_each_pattern_once() -> None:
    order = OrderList.sequential(3)
    assert order.entries == (0, 1, 2)
    assert order.length == 3
    assert order.entries[1] == 1


@pytest.mark.parametrize("clock", [(0, 125), (6, 0)])
def test_a_stopped_clock_is_rejected(clock: tuple[int, int]) -> None:
    speed, tempo = clock
    with pytest.raises(ValueError):
        Playback(speed=speed, tempo=tempo)

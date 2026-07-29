import pytest

from tests.conftest import make_sample
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.keymap import KeyAssignment, routed_keymap
from trackmod.core.instruments.transfer import combine, extract, held
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.core.notes.pitch import Note
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.song import Song


def test_a_unit_carries_only_the_samples_its_keys_reach(song: Song) -> None:
    # The router names samples 1 and 2 of the song's three, so the third has no business travelling.
    unit = extract(song, 1)
    assert len(unit.samples) == 2
    assert unit.samples == (song.samples[1], song.samples[2])


def test_an_extracted_keymap_is_numbered_from_zero(song: Song) -> None:
    unit = extract(song, 1)
    assert unit.instrument.samples == (0, 1)
    assert unit.instrument.assignment(Note(60)) == KeyAssignment(sample=0, note=Note(60))
    assert unit.instrument.assignment(Note(61)) == KeyAssignment(sample=1, note=Note(60))


def test_extraction_keeps_everything_but_the_routing(song: Song) -> None:
    # Verbatim is the contract: a caller grafting an instrument gets the voice it listened to.
    original = song.instruments[0]
    carried = extract(song, 0).instrument
    assert carried.volume_envelope == original.volume_envelope
    assert carried.fadeout == original.fadeout
    assert carried.new_note_action == original.new_note_action
    assert carried.name == original.name


def test_an_instrument_routing_no_key_carries_no_samples() -> None:
    reserved = Instrument(name="", keymap=routed_keymap({}))
    unit = InstrumentUnit(instrument=reserved, samples=())
    assert unit.samples == ()
    assert combine((unit,)) == ((reserved,), ())


def test_a_unit_naming_a_sample_it_does_not_hold_is_rejected() -> None:
    router = Instrument(name="router", keymap=routed_keymap({Note(60): KeyAssignment(sample=3, note=Note(60))}))
    with pytest.raises(ValueError):
        InstrumentUnit(instrument=router, samples=(make_sample("lone"),))


def test_combining_lays_each_units_samples_out_in_one_run(song: Song) -> None:
    units = (extract(song, 1), extract(song, 0))
    instruments, samples = combine(units)
    assert samples == (song.samples[1], song.samples[2], song.samples[0])
    assert instruments[0].samples == (0, 1)
    assert instruments[1].samples == (2,)


def test_a_song_states_every_instrument_it_holds_as_a_unit(song: Song) -> None:
    assert held(song) == tuple(extract(song, index) for index in range(len(song.instruments)))


def test_a_song_holding_no_instrument_states_no_unit(song: Song) -> None:
    assert held(song.model_copy(update={"instruments": (), "samples": ()})) == ()


def test_a_song_rebuilt_from_its_units_plays_what_it_played(song: Song) -> None:
    # The round trip is the whole point: what a unit carries has to reassemble into the same music.
    instruments, samples = combine(held(song))
    rebuilt = Song(
        name=song.name,
        channels=song.channels,
        patterns=song.patterns,
        order=song.order,
        instruments=instruments,
        samples=samples,
        playback=song.playback,
    )
    for original, carried in zip(song.instruments, rebuilt.instruments):
        for key in range(len(original.keymap)):
            here, there = original.assignment(Note(key)), carried.assignment(Note(key))
            assert (here is None) == (there is None)
            if here is not None and there is not None:
                assert here.note == there.note
                assert song.samples[here.sample] == rebuilt.samples[there.sample]


def test_a_unit_survives_a_song_that_renumbers_its_table(song: Song) -> None:
    # Grafting into a song whose table already holds something is where a stale index would show.
    resident, incoming = extract(song, 0), extract(song, 1)
    instruments, samples = combine((resident, incoming))
    assert samples[instruments[1].samples[0]] == incoming.samples[0]
    assert samples[instruments[0].samples[0]] == resident.samples[0]


def test_rerouting_leaves_silent_keys_silent(song: Song) -> None:
    router = song.instruments[1]
    moved = router.rerouted({sample: sample + 10 for sample in router.samples})
    assert moved.assignment(Note(0)) is None
    assert moved.samples == tuple(sample + 10 for sample in router.samples)


def test_rerouting_without_a_position_for_a_reached_sample_is_refused(song: Song) -> None:
    with pytest.raises(KeyError):
        song.instruments[1].rerouted({})


def test_an_instrument_out_of_range_is_refused(song: Song) -> None:
    with pytest.raises(IndexError):
        extract(song, len(song.instruments))

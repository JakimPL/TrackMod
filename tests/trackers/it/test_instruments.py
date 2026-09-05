from trackmod.core.notes.pitch import Note
from trackmod.core.repairs.report import Repairs
from trackmod.spec.pitch import NOTE_COUNT
from trackmod.trackers.it.instruments.keymap import HIGHEST_KEY, note_map, parse_keymap


def test_a_note_map_key_sounding_past_the_keyboard_is_drawn_onto_the_highest_key() -> None:
    # Trackers leave whatever they like in the played-note column of a key routed nowhere, and real
    # files carry bytes past the last key this model numbers.
    repairs = Repairs()
    rows = tuple((200, 1) for _ in range(NOTE_COUNT))
    keymap = parse_keymap(rows, subject="instrument 0", repairs=repairs)
    assert keymap[0] is not None
    assert keymap[0].note == Note(HIGHEST_KEY)
    assert repairs.entries == (("instrument 0", f"note map key sounding 200 drawn to {HIGHEST_KEY}"),)


def test_a_note_map_inside_the_keyboard_round_trips_untouched() -> None:
    repairs = Repairs()
    rows = tuple((key, 1) for key in range(NOTE_COUNT))
    keymap = parse_keymap(rows, subject="instrument 0", repairs=repairs)
    assert note_map(keymap) == rows
    assert repairs.entries == ()

import pytest

from trackmod.core.notes.command import NoteCommand
from trackmod.core.notes.pitch import Note
from trackmod.spec.grid import EMPTY
from trackmod.spec.pitch import NOTE_COUNT, RATE_NOTE
from trackmod.trackers.s3m.note import decode_note, encode_note, stored_key, stored_note
from trackmod.trackers.s3m.spec.cells import NoteByte
from trackmod.trackers.s3m.spec.keys import BASE_NOTE, MAX_NOTE

REFERENCE_BYTE = 0x40


def test_the_byte_a_sample_sounds_its_own_rate_at_spells_the_reference_key() -> None:
    # Rendering a module holding this byte plays a waveform at exactly the rate its record states, which
    # is the key the shared model measures a stored rate by.
    assert decode_note(REFERENCE_BYTE) == Note(RATE_NOTE)
    assert stored_key(Note(RATE_NOTE)) == REFERENCE_BYTE


@pytest.mark.parametrize("key", range(BASE_NOTE, NOTE_COUNT))
def test_every_key_this_column_reaches_survives_the_byte_it_is_stored_as(key: int) -> None:
    byte = stored_key(Note(key))
    assert byte is not None
    assert decode_note(byte) == Note(key)


@pytest.mark.parametrize("key", range(BASE_NOTE))
def test_the_keys_below_the_octave_this_column_counts_from_have_no_byte(key: int) -> None:
    assert stored_key(Note(key)) is None
    with pytest.raises(ValueError, match="below the octave"):
        encode_note(Note(key))


def test_a_semitone_nibble_past_an_octave_names_no_key() -> None:
    assert decode_note(0x4C) is None
    assert decode_note(0x4F) is None


def test_a_byte_reaching_past_the_keys_the_model_numbers_names_none() -> None:
    assert decode_note(0x97) is None
    assert decode_note(0x8B) == Note(MAX_NOTE)


def test_the_column_silences_a_channel_and_names_no_other_command() -> None:
    assert decode_note(int(NoteByte.CUT)) is NoteCommand.CUT
    assert encode_note(NoteCommand.CUT) == int(NoteByte.CUT)
    for command in (NoteCommand.OFF, NoteCommand.FADE):
        assert stored_key(command) is None
        with pytest.raises(ValueError, match="silences a channel"):
            encode_note(command)


def test_an_absent_note_stays_absent_through_the_grid() -> None:
    assert stored_note(EMPTY) == EMPTY
    assert stored_note(RATE_NOTE) == REFERENCE_BYTE
    with pytest.raises(ValueError, match="silences a channel"):
        stored_note(int(NoteCommand.OFF))

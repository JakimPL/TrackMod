import numpy as np
import pytest

from trackmod.core.notes.command import NoteCommand
from trackmod.core.notes.pitch import Note
from trackmod.spec.grid import EMPTY
from trackmod.spec.pitch import NOTES_PER_OCTAVE, RATE_NOTE, REFERENCE_RATE
from trackmod.trackers.mod.note import (
    PERIODS,
    STORED_PERIODS,
    decode_period,
    encode_note,
    scaled_period,
    stored_note,
)
from trackmod.trackers.mod.spec.periods import (
    AMIGA_PERIODS,
    BASE_NOTE,
    CANONICAL_MAX_NOTE,
    CANONICAL_MIN_NOTE,
    FINETUNE_PERIODS,
    FINETUNE_RATES,
    HALF_SEMITONE,
    MAX_PERIOD,
    MIN_NOTE,
    TABULATED_OCTAVES,
)
from trackmod.trackers.mod.tuning import finetune_for, finetune_rate

SOUNDED_KEYS = tuple(note for note, period in enumerate(PERIODS) if period)


def test_the_tabulated_octaves_are_the_keys_the_original_tracker_wrote() -> None:
    assert len(AMIGA_PERIODS) == len(TABULATED_OCTAVES) * NOTES_PER_OCTAVE
    assert CANONICAL_MIN_NOTE == BASE_NOTE
    assert CANONICAL_MAX_NOTE - CANONICAL_MIN_NOTE + 1 == len(AMIGA_PERIODS)


def test_the_reference_key_sounds_at_the_reference_rate() -> None:
    # The whole tuning hangs off this one pair: the key the shared model measures a rate at is the key
    # the tabulated middle octave opens on, and its period is what every finetune row is scaled against.
    assert PERIODS[RATE_NOTE] == TABULATED_OCTAVES[1][0]
    assert finetune_rate(0) == REFERENCE_RATE


def test_every_tabulated_key_keeps_the_period_the_tracker_stated() -> None:
    for index, period in enumerate(AMIGA_PERIODS):
        assert PERIODS[BASE_NOTE + index] == period


def test_a_key_an_octave_up_sounds_at_half_the_period() -> None:
    # This is what carries the three tabulated octaves to the rest of the keyboard, and it has to hold
    # to within the tolerance a period is read at, or a scaled key would read back as its neighbour.
    for note in SOUNDED_KEYS:
        lower = note - NOTES_PER_OCTAVE
        if lower >= 0 and PERIODS[lower]:
            assert PERIODS[note] / PERIODS[lower] == pytest.approx(0.5, rel=HALF_SEMITONE - 1)


def test_every_key_it_sounds_reads_back_as_itself() -> None:
    for note in SOUNDED_KEYS:
        recovered = decode_period(PERIODS[note])
        assert recovered is not None
        assert recovered.value == note


def test_no_two_keys_share_a_period() -> None:
    assert len(set(STORED_PERIODS)) == len(STORED_PERIODS)


def test_the_lowest_key_is_where_the_twelve_bit_period_runs_out() -> None:
    # This is the whole argument for the structural floor: one key lower needs a period the cell cannot
    # hold, so the field itself is what decides how deep this format reaches.
    assert PERIODS[MIN_NOTE] <= MAX_PERIOD
    assert scaled_period(MIN_NOTE - 1) > MAX_PERIOD


def test_a_period_close_to_a_key_reads_as_that_key() -> None:
    # Every tracker of this lineage rounded its own table, so a period a digit away from the tabulated
    # one is the key it comes closest to rather than a value with no meaning.
    for period, expected in ((429, 60), (427, 60), (907, 47), (906, 47), (571, 55)):
        recovered = decode_period(period)
        assert recovered is not None
        assert recovered.value == expected


def test_a_period_between_the_keys_names_none_of_them() -> None:
    assert decode_period(0) is None
    assert decode_period(2) is None


def test_a_key_the_table_sounds_is_written_as_the_period_it_sounds_at() -> None:
    assert encode_note(Note(RATE_NOTE)) == PERIODS[RATE_NOTE]
    assert stored_note(RATE_NOTE) == PERIODS[RATE_NOTE]


def test_the_note_column_states_a_pitch_and_no_command() -> None:
    with pytest.raises(ValueError, match="OFF"):
        encode_note(NoteCommand.OFF)

    with pytest.raises(ValueError, match="CUT"):
        encode_note(NoteCommand.CUT)


def test_a_key_below_the_period_field_is_refused() -> None:
    with pytest.raises(ValueError, match="past the twelve bits"):
        encode_note(Note(MIN_NOTE - 1))


def test_an_absent_note_stays_absent() -> None:
    assert stored_note(EMPTY) == EMPTY


def test_the_sixteen_finetune_rows_step_an_eighth_of_a_semitone() -> None:
    # A row is stated as the key it opens on, and the rate follows from the ratio to the untrimmed row,
    # so the rates and the periods cannot drift apart.
    assert len(FINETUNE_PERIODS) == len(FINETUNE_RATES)
    for index, period in enumerate(FINETUNE_PERIODS):
        assert FINETUNE_RATES[index] == round(REFERENCE_RATE * AMIGA_PERIODS[0] / period)

    steps = [NOTES_PER_OCTAVE * np.log2(FINETUNE_RATES[index + 1] / FINETUNE_RATES[index]) for index in range(7)]
    assert all(step == pytest.approx(0.125, abs=0.005) for step in steps)


def test_the_lowest_row_sits_a_semitone_below_the_highest_trim() -> None:
    # The eight rows below the reference are the tabulated ones shifted by a semitone, which is why the
    # lowest of them lands almost exactly one twelfth of an octave down.
    assert NOTES_PER_OCTAVE * np.log2(FINETUNE_RATES[8] / FINETUNE_RATES[0]) == pytest.approx(-1.0, abs=0.01)


def test_every_finetune_row_is_recovered_from_the_rate_it_plays() -> None:
    for finetune in range(len(FINETUNE_RATES)):
        assert finetune_for(finetune_rate(finetune)) == finetune


def test_a_rate_between_two_rows_takes_the_nearer_one() -> None:
    between = (FINETUNE_RATES[0] + FINETUNE_RATES[1]) // 2
    assert finetune_for(between + 10) == 1
    assert finetune_for(between - 10) == 0

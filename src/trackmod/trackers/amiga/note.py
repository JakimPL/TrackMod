import bisect
from typing import Final

from trackmod.core.notes.codec import decode_note as decode_shared_note
from trackmod.core.notes.command import NoteCommand, NoteValue
from trackmod.core.notes.pitch import Note
from trackmod.spec.grid import EMPTY
from trackmod.spec.pitch import NOTE_COUNT, NOTES_PER_OCTAVE
from trackmod.trackers.amiga.spec.cells import NO_PERIOD, UNSTORABLE
from trackmod.trackers.amiga.spec.periods import (
    AMIGA_PERIODS,
    BASE_NOTE,
    BASE_OCTAVES,
    HALF_SEMITONE,
    MAX_PERIOD,
    TOP_OCTAVE,
)


def scaled_period(note: int) -> int:
    """The Amiga period one key sounds at, the stated three octaves halved or doubled to reach the rest.

    Amiga ProTracker tabulates three octaves and every tracker that reached past them scaled the table
    by octaves, which is exact: an octave is a doubling of the period, so a key outside the table sounds
    at a stated one shifted by whole octaves.
    """
    octave, index = divmod(note - BASE_NOTE, NOTES_PER_OCTAVE)
    if 0 <= octave < BASE_OCTAVES:
        return AMIGA_PERIODS[note - BASE_NOTE]

    if octave < 0:
        return AMIGA_PERIODS[index] << -octave

    return round(AMIGA_PERIODS[TOP_OCTAVE + index] / (1 << (octave - BASE_OCTAVES + 1)))


PERIODS: Final = tuple(
    period if period <= MAX_PERIOD else NO_PERIOD for period in (scaled_period(note) for note in range(NOTE_COUNT))
)

SOUNDED: Final = tuple(sorted((period, note) for note, period in enumerate(PERIODS) if period))
STORED_PERIODS: Final = tuple(period for period, _ in SOUNDED)


def nearest(period: int) -> tuple[int, int]:
    """The stated period closest to ``period`` in pitch, and the key it sounds."""
    index = bisect.bisect_left(STORED_PERIODS, period)
    reached = SOUNDED[max(index - 1, 0) : index + 1]
    return min(reached, key=lambda stated: max(period / stated[0], stated[0] / period))


def decode_period(period: int) -> Note | None:
    """The key a stored period sounds, or ``None`` when it lands on no key this lineage tabulates.

    A tracker writes the period its own table holds and the tables disagree in their last digit, so a
    period is read as the key it comes closest to. A period further than half a semitone from every key
    states a pitch outside the three octaves this lineage tabulates and the octaves they scale to.
    """
    if period <= NO_PERIOD:
        return None

    stated, note = nearest(period)
    reach = max(period / stated, stated / period)
    return Note(note) if reach <= HALF_SEMITONE else None


def stored_period(note: NoteValue) -> int | None:
    """The period this lineage stores for ``note``, or ``None`` when its note column cannot state it.

    The column holds a period, so it states a pitch and nothing else: a command acting on a playing
    voice has a period only where it names a pitch, and so has a key deep enough to overflow the field.
    """
    match note:
        case NoteCommand():
            return None
        case Note():
            period = PERIODS[note.value]
            return period if period != NO_PERIOD else None


def refusal(note: NoteValue) -> str:
    """Why this lineage's note column cannot state ``note``."""
    match note:
        case NoteCommand():
            return f"the note column stores a period and has none for {note.name}"
        case Note():
            return f"key {note} sounds at a period past the twelve bits a cell holds"


def encode_note(note: NoteValue) -> int:
    """The period this lineage's note column stores for a note-column entry.

    Raises:
        ValueError: when the note column cannot state ``note``.
    """
    period = stored_period(note)
    if period is None:
        raise ValueError(refusal(note))

    return period


NOTE_PERIODS: Final = tuple(
    UNSTORABLE if period is None else period
    for period in (stored_period(decode_shared_note(code)) for code in range(NOTE_COUNT + len(NoteCommand)))
)


def stored_note(code: int) -> int:
    """The period a grid note code is written as, leaving an absent note absent.

    Raises:
        ValueError: when the code names a note this lineage's note column cannot state.
    """
    if code == EMPTY:
        return EMPTY

    period = NOTE_PERIODS[code]
    if period == UNSTORABLE:
        raise ValueError(refusal(decode_shared_note(code)))

    return period

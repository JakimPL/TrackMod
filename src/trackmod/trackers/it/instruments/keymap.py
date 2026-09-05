from typing import Final

from trackmod.binary.records.values import ArrayValue
from trackmod.core.instruments.keymap import KeyAssignment, Keymap
from trackmod.core.notes.pitch import Note
from trackmod.core.repairs.report import Repairs
from trackmod.spec.pitch import NOTE_COUNT
from trackmod.trackers.it.spec.defaults import NO_SAMPLE

HIGHEST_KEY: Final = NOTE_COUNT - 1


def note_map(keymap: Keymap) -> tuple[tuple[int, int], ...]:
    """The ``(played note, sample number)`` pair each key stores.

    Sample numbers are one-based here, so zero is what silences a key; an unmapped key still names its
    own pitch, which is the identity mapping a tracker writes for an instrument with nothing routed yet.
    """
    return tuple(
        (key, NO_SAMPLE) if assignment is None else (assignment.note.value, assignment.sample + 1)
        for key, assignment in enumerate(keymap)
    )


def sounded_note(played: int, *, subject: str, repairs: Repairs) -> Note:
    """The note one key of a stored map sounds, drawn onto the keyboard the shared model numbers.

    A key routed nowhere carries whatever its tracker left in the note column, so a byte past the last
    key is read as the highest key there is.
    """
    if played <= HIGHEST_KEY:
        return Note(played)

    repairs.made(f"note map key sounding {played} drawn to {HIGHEST_KEY}", subject=subject)
    return Note(HIGHEST_KEY)


def parse_keymap(rows: ArrayValue, *, subject: str, repairs: Repairs) -> Keymap:
    """Rebuild a keymap from the stored ``(played note, sample number)`` pairs."""
    return tuple(
        (
            None
            if sample == NO_SAMPLE
            else KeyAssignment(
                sample=sample - 1,
                note=sounded_note(played, subject=subject, repairs=repairs),
            )
        )
        for played, sample in rows
    )

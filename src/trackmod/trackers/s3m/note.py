from typing import Final

from trackmod.core.notes.codec import decode_note as decode_shared_note
from trackmod.core.notes.command import NoteCommand, NoteValue
from trackmod.core.notes.pitch import Note
from trackmod.spec.grid import EMPTY
from trackmod.spec.pitch import NOTE_COUNT, NOTES_PER_OCTAVE
from trackmod.spec.width import NIBBLE_MAX
from trackmod.trackers.s3m.spec.cells import NoteByte
from trackmod.trackers.s3m.spec.keys import BASE_NOTE, OCTAVE_SHIFT, SEMITONE_MASK

UNSTORABLE: Final = -1

COMMAND_BYTES: Final[dict[NoteCommand, NoteByte]] = {NoteCommand.CUT: NoteByte.CUT}
BYTE_COMMANDS: Final[dict[int, NoteCommand]] = {int(byte): command for command, byte in COMMAND_BYTES.items()}


def stated_key(byte: int) -> int | None:
    """The key a stored note byte sounds, or ``None`` when its two nibbles name none.

    The byte spells a key as an octave over a semitone, and the octave it counts from is the one above
    the model's own — so the deepest key this format reaches is the model's C-1 and its lowest octave
    has no byte at all. A semitone nibble past the twelve in an octave names nothing.
    """
    semitone = byte & SEMITONE_MASK
    if semitone >= NOTES_PER_OCTAVE:
        return None

    key = NOTES_PER_OCTAVE * (byte >> OCTAVE_SHIFT) + semitone + BASE_NOTE
    return key if key < NOTE_COUNT else None


def decode_note(byte: int) -> NoteValue | None:
    """The note-column entry a stored byte states, or ``None`` when it names nothing this format defines."""
    command = BYTE_COMMANDS.get(byte)
    if command is not None:
        return command

    key = stated_key(byte)
    return Note(key) if key is not None else None


def stored_key(note: NoteValue) -> int | None:
    """The byte this format's note column stores ``note`` as, or ``None`` when it cannot state it.

    The column holds one key-off command and no others, and the octave it counts from leaves the model's
    deepest twelve keys with no byte to sit in.
    """
    match note:
        case NoteCommand():
            byte = COMMAND_BYTES.get(note)
            return int(byte) if byte is not None else None
        case Note():
            octave, semitone = divmod(note.value - BASE_NOTE, NOTES_PER_OCTAVE)
            return (octave << OCTAVE_SHIFT) | semitone if 0 <= octave <= NIBBLE_MAX else None


def refusal(note: NoteValue) -> str:
    """Why this format's note column cannot state ``note``."""
    match note:
        case NoteCommand():
            return f"the note column silences a channel and has no term for {note.name}"
        case Note():
            return f"key {note} lies below the octave this format's note column counts from"


def encode_note(note: NoteValue) -> int:
    """The byte this format's note column stores for a note-column entry.

    Raises:
        ValueError: when the note column cannot state ``note``.
    """
    byte = stored_key(note)
    if byte is None:
        raise ValueError(refusal(note))

    return byte


NOTE_BYTES: Final = tuple(
    UNSTORABLE if byte is None else byte
    for byte in (stored_key(decode_shared_note(code)) for code in range(NOTE_COUNT + len(NoteCommand)))
)


def stored_note(code: int) -> int:
    """The byte a grid note code is written as, leaving an absent note absent.

    Raises:
        ValueError: when the code names a note this format's note column cannot state.
    """
    if code == EMPTY:
        return EMPTY

    byte = NOTE_BYTES[code]
    if byte == UNSTORABLE:
        raise ValueError(refusal(decode_shared_note(code)))

    return byte

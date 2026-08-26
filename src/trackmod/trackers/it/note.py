from typing import Final

from trackmod.core.notes.codec import decode_note as decode_shared_note
from trackmod.core.notes.command import NoteCommand, NoteValue
from trackmod.core.notes.pitch import Note
from trackmod.spec.pitch import NOTE_COUNT
from trackmod.trackers.it.spec.cells import NoteByte

COMMAND_BYTES: Final[dict[NoteCommand, NoteByte]] = {
    NoteCommand.OFF: NoteByte.OFF,
    NoteCommand.CUT: NoteByte.CUT,
    NoteCommand.FADE: NoteByte.FADE,
}
BYTE_COMMANDS: Final[dict[int, NoteCommand]] = {int(byte): command for command, byte in COMMAND_BYTES.items()}


def encode_note(note: NoteValue) -> int:
    """The note byte this format stores for a note-column entry.

    Impulse Tracker numbers its keyboard from C-0 exactly as the shared model does, so a key needs no
    offset; the commands occupy the top of the byte range.
    """
    match note:
        case NoteCommand():
            return int(COMMAND_BYTES[note])
        case Note():
            return note.value


def decode_note(byte: int) -> NoteValue | None:
    """The note-column entry a stored note byte stands for, or ``None`` when it names nothing.

    The keys this format numbers stop at ``NOTE_COUNT`` and its commands sit at the top of the byte
    range, so the values between them state something this vocabulary has no term for.
    """
    command = BYTE_COMMANDS.get(byte)
    if command is not None:
        return command

    return Note(byte) if byte < NOTE_COUNT else None


NOTE_BYTES: Final = tuple(encode_note(decode_shared_note(code)) for code in range(NOTE_COUNT + len(NoteCommand)))

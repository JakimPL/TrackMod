from trackmod.core.instruments.keymap import KeyAssignment, Keymap
from trackmod.core.notes.pitch import Note
from trackmod.spec.pitch import NOTE_COUNT
from trackmod.trackers.xm.spec.sizes import KEYMAP_NOTES


def stored_keymap(slots: tuple[int | None, ...], *, length: int) -> bytes:
    """The keymap block a stored instrument carries: one sample position per key it numbers.

    A silent key names the position just past the ``length`` samples the instrument stores, which no
    sample occupies, so :func:`parse_keymap` reads that key back as silent.
    """
    return bytes(length if slot is None else slot for slot in slots)


def parse_keymap(raw: bytes, *, offset: int, length: int) -> Keymap:
    """Rebuild a keymap from the stored sample positions, resolved against the module's samples.

    A key reads as silent where it falls outside the keys this format numbers, or where it names a
    position past the ``length`` samples the instrument stores, which is how :func:`stored_keymap`
    writes one.
    """
    return tuple(
        (KeyAssignment(sample=offset + raw[key], note=Note(key)) if key < KEYMAP_NOTES and raw[key] < length else None)
        for key in range(NOTE_COUNT)
    )

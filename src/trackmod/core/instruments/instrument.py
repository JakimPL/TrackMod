from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel

from trackmod.core.envelopes.envelope import Envelope
from trackmod.core.envelopes.kind import EnvelopeKind
from trackmod.core.instruments.behavior import (
    DuplicateAction,
    DuplicateCheck,
    NewNoteAction,
)
from trackmod.core.instruments.keymap import KeyAssignment, Keymap
from trackmod.core.notes.pitch import Note
from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Fadeout, InstrumentVolume, Panning
from trackmod.spec.levels import MAX_INSTRUMENT_VOLUME, NO_FADEOUT


class Instrument(BaseModel):
    """A named routing of keys onto samples, with the envelopes every voice it starts follows.

    A keymap names positions in the sample table of the song this instrument belongs to. To carry an
    instrument between songs, pair it with its own samples as an
    :class:`~trackmod.core.instruments.unit.InstrumentUnit`.

    Args:
        name: The instrument's title, as a tracker shows it.
        keymap: Exactly 120 entries, one per key from C-0 upward. Each is either ``None`` for a silent
            key or a :class:`~trackmod.core.instruments.keymap.KeyAssignment` naming the sample to play
            and the note to play it at. Build one with ``pitched_keymap`` or ``routed_keymap``.
        volume_envelope: The curve a voice's level follows, or ``None`` to leave the level alone.
        panning_envelope: The curve a voice's position follows, or ``None``.
        pitch_envelope: The curve a voice's pitch follows, or ``None``.
        fadeout: How fast a released voice fades, as a rate rather than a length of time. Defaults to
            no fade, which holds a voice at its level for as long as it plays.
        global_volume: A level applied to every voice this instrument starts, ``0..128``.
        panning: A position on the shared ``0..255`` field, or ``None`` to leave it to the tracker.
        new_note_action: What happens to a playing voice when the same channel starts a new note.
        duplicate_check: What makes two voices of this instrument count as duplicates.
        duplicate_action: What happens to the voice a duplicate check finds.

    Raises:
        ValidationError: when ``keymap`` does not hold exactly 120 entries.
    """

    model_config = FROZEN

    name: str
    keymap: Keymap
    volume_envelope: Envelope | None = None
    panning_envelope: Envelope | None = None
    pitch_envelope: Envelope | None = None
    fadeout: Fadeout = NO_FADEOUT
    global_volume: InstrumentVolume = MAX_INSTRUMENT_VOLUME
    panning: Panning | None = None
    new_note_action: NewNoteAction = NewNoteAction.CUT
    duplicate_check: DuplicateCheck = DuplicateCheck.OFF
    duplicate_action: DuplicateAction = DuplicateAction.CUT

    @property
    def samples(self) -> tuple[int, ...]:
        """Every sample the keymap reaches, in the order the keys first name them."""
        seen: dict[int, None] = {}
        for assignment in self.keymap:
            if assignment is not None:
                seen[assignment.sample] = None

        return tuple(seen)

    def envelope(self, kind: EnvelopeKind) -> Envelope | None:
        """The envelope of one kind this instrument carries.

        Args:
            kind: Which of the three envelopes to read.

        Returns:
            The envelope, or ``None`` when this instrument leaves that property alone.
        """
        match kind:
            case EnvelopeKind.VOLUME:
                return self.volume_envelope
            case EnvelopeKind.PANNING:
                return self.panning_envelope
            case EnvelopeKind.PITCH:
                return self.pitch_envelope

    def assignment(self, note: Note) -> KeyAssignment | None:
        """What pressing one key on this instrument plays.

        Args:
            note: The key pressed, counted in semitones above C-0.

        Returns:
            The sample to play and the note to play it at, or ``None`` when that key is silent.
        """
        return self.keymap[note.value]

    def rerouted(self, positions: Mapping[int, int]) -> Instrument:
        """Move every sample this instrument's keys name to a new position.

        A keymap indexes into the sample table of the song it belongs to, so carrying an instrument to
        another table means renumbering those positions. Only the routing moves: the keys, the notes
        they play, and every envelope, level and behavior stay as they were.

        Args:
            positions: The new position for each sample the keymap reaches, keyed by its current one.
                Every entry of :attr:`samples` must appear.

        Returns:
            A copy of this instrument with its keymap renumbered.

        Raises:
            KeyError: when a sample the keymap reaches is missing from ``positions``.
            ValidationError: when a new position is negative.
        """
        keymap = tuple(
            (None if assignment is None else KeyAssignment(sample=positions[assignment.sample], note=assignment.note))
            for assignment in self.keymap
        )
        return self.model_copy(update={"keymap": keymap})

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel

from trackmod.core.envelopes.envelope import Envelope
from trackmod.core.envelopes.kind import EnvelopeKind
from trackmod.core.instruments.behaviour import (
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
    """A named routing of keys onto samples, with the envelopes every voice it starts follows."""

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
        """The envelope of one kind this instrument carries, if any."""
        match kind:
            case EnvelopeKind.VOLUME:
                return self.volume_envelope
            case EnvelopeKind.PANNING:
                return self.panning_envelope
            case EnvelopeKind.PITCH:
                return self.pitch_envelope

    def assignment(self, note: Note) -> KeyAssignment | None:
        """What pressing ``note`` on this instrument plays."""
        return self.keymap[note.value]

    def rerouted(self, positions: Mapping[int, int]) -> Instrument:
        """This instrument with every sample its keys name moved to the position ``positions`` gives it.

        A keymap indexes into the sample table of the song it belongs to, so carrying an instrument to
        another table means restating those positions. The routing is the only part that moves: the
        keys, the notes they sound, and every envelope, level and behaviour stay as stated.

        Raises:
            KeyError: when a sample the keymap reaches is left unnamed by ``positions``.
        """
        keymap = tuple(
            None if assignment is None else KeyAssignment(sample=positions[assignment.sample], note=assignment.note)
            for assignment in self.keymap
        )
        return self.model_copy(update={"keymap": keymap})

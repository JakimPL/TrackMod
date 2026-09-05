from typing import Final

from trackmod.binary.nibble import decimal_byte, join_nibbles
from trackmod.core.effects.effect import Effect
from trackmod.limits.guard import require_range
from trackmod.trackers.s3m.effects.command import S3MEffect, S3MExtended
from trackmod.trackers.s3m.panning import stored_position
from trackmod.trackers.s3m.spec.effects import (
    NIBBLE_PARAMETER,
    ORDER_PARAMETER,
    PANNING_PARAMETER,
    ROW_PARAMETER,
    SPEED_PARAMETER,
    TEMPO_PARAMETER,
)


def extended(sub_command: S3MExtended, value: int) -> Effect:
    """An ``S`` effect carrying one sub-command and its four-bit value.

    Raises:
        ValueError: when ``value`` exceeds four bits.
    """
    return Effect(command=S3MEffect.EXTENDED, parameter=join_nibbles(sub_command, value))


class S3MEffects:
    """The shared effect vocabulary as Scream Tracker 3 spells it.

    Speed and tempo take a command each, which is where Impulse Tracker inherited the arrangement from:
    ``A`` sets the ticks a row lasts and ``T`` the rate they run at.
    """

    def set_speed(self, ticks: int) -> Effect:
        """Set the ticks each row lasts."""
        return Effect(
            command=S3MEffect.SET_SPEED,
            parameter=require_range(ticks, bound=SPEED_PARAMETER, subject="speed"),
        )

    def set_tempo(self, beats_per_minute: int) -> Effect:
        """Set the tick rate, in beats per minute."""
        return Effect(
            command=S3MEffect.SET_TEMPO,
            parameter=require_range(beats_per_minute, bound=TEMPO_PARAMETER, subject="tempo"),
        )

    def position_jump(self, order: int) -> Effect:
        """Continue playback at the given order-list position."""
        return Effect(
            command=S3MEffect.POSITION_JUMP,
            parameter=require_range(order, bound=ORDER_PARAMETER, subject="order"),
        )

    def pattern_break(self, row: int) -> Effect:
        """End the pattern and continue at the given row of the next order.

        The parameter is read a decimal digit to a nibble, the way Amiga ProTracker read it and every
        tracker after it kept reading it, so a break to row 16 is stored as ``0x16``.
        """
        return Effect(
            command=S3MEffect.PATTERN_BREAK,
            parameter=decimal_byte(require_range(row, bound=ROW_PARAMETER, subject="row")),
        )

    def note_delay(self, ticks: int) -> Effect:
        """Delay this cell's note by the given number of ticks into the row."""
        return extended(S3MExtended.NOTE_DELAY, require_range(ticks, bound=NIBBLE_PARAMETER, subject="delay"))

    def note_cut(self, ticks: int) -> Effect:
        """Silence this channel the given number of ticks into the row."""
        return extended(S3MExtended.NOTE_CUT, require_range(ticks, bound=NIBBLE_PARAMETER, subject="cut"))

    def volume_slide(self, *, up: int, down: int) -> Effect:
        """Slide the channel volume by one nibble per tick, in exactly one direction.

        Raises:
            ValueError: when both directions are asked for at once, which the parameter cannot express.
        """
        if up and down:
            raise ValueError(f"a volume slide runs one way, got up {up} and down {down}")

        require_range(up, bound=NIBBLE_PARAMETER, subject="slide up")
        require_range(down, bound=NIBBLE_PARAMETER, subject="slide down")
        return Effect(command=S3MEffect.VOLUME_SLIDE, parameter=join_nibbles(up, down))

    def set_panning(self, position: int) -> Effect:
        """Place the channel on the stereo field, on the shared 0..255 scale.

        The parameter counts the field in a hundred and twenty-nine steps, which is the finer of the two
        grids this format states a position on and the one a song reaches an exact place with.
        """
        return Effect(
            command=S3MEffect.SET_PANNING,
            parameter=stored_position(require_range(position, bound=PANNING_PARAMETER, subject="panning")),
        )


S3M_EFFECTS: Final = S3MEffects()

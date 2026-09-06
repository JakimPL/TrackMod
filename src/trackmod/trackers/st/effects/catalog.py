from typing import Final

from trackmod.binary.nibble import decimal_byte
from trackmod.core.effects.effect import Effect
from trackmod.limits.guard import require_range
from trackmod.trackers.st.effects.command import STEffect
from trackmod.trackers.st.spec.effects import (
    ORDER_PARAMETER,
    ROW_PARAMETER,
    SPEED_PARAMETER,
)


class STEffects:
    """The shared effect vocabulary as the fifteen-sample trackers spell it.

    Seven commands is the whole of it, so this catalogue spells the three intents they cover and names
    the five they leave to the trackers that came after. A caller reaching for one of those five is told
    which command it would need and which format numbers it, which is what makes the gap legible rather
    than a cell that plays as something else.

    Raises:
        ValueError: from every intent this format numbers no command for.
    """

    def set_speed(self, ticks: int) -> Effect:
        """Set the ticks each row lasts."""
        return Effect(
            command=STEffect.SET_SPEED,
            parameter=require_range(ticks, bound=SPEED_PARAMETER, subject="speed"),
        )

    def set_tempo(self, beats_per_minute: int) -> Effect:
        """Set the tick rate, in the tracker's beats-per-minute units.

        Raises:
            ValueError: always. This format runs at the one rate its clock states, and Amiga ProTracker
                is where the ``F`` command grew the second half that sets the beats per minute.
        """
        raise ValueError(
            f"tempo {beats_per_minute} needs a command this format numbers none for, "
            "which Amiga ProTracker spells with F above 0x20"
        )

    def position_jump(self, order: int) -> Effect:
        """Continue playback at the given order-list position."""
        return Effect(
            command=STEffect.POSITION_JUMP,
            parameter=require_range(order, bound=ORDER_PARAMETER, subject="order"),
        )

    def pattern_break(self, row: int) -> Effect:
        """End the pattern and continue at the given row of the next order.

        The parameter reads a decimal digit to a nibble, which is the reading Amiga ProTracker inherited
        from here, so a break to row 16 is stored as ``0x16``.
        """
        return Effect(
            command=STEffect.PATTERN_BREAK,
            parameter=decimal_byte(require_range(row, bound=ROW_PARAMETER, subject="row")),
        )

    def note_delay(self, ticks: int) -> Effect:
        """Delay this cell's note by the given number of ticks into the row.

        Raises:
            ValueError: always. The ``E`` command that carries the sub-commands is Amiga ProTracker's.
        """
        raise ValueError(
            f"a delay of {ticks} ticks needs a command this format numbers none for, "
            "which Amiga ProTracker spells with ED"
        )

    def note_cut(self, ticks: int) -> Effect:
        """Silence this channel the given number of ticks into the row.

        Raises:
            ValueError: always. The ``E`` command that carries the sub-commands is Amiga ProTracker's.
        """
        raise ValueError(
            f"a cut at {ticks} ticks needs a command this format numbers none for, "
            "which Amiga ProTracker spells with EC"
        )

    def volume_slide(self, *, up: int, down: int) -> Effect:
        """Slide the channel volume by one nibble per tick, in exactly one direction.

        Raises:
            ValueError: always. A level here is set outright with ``C``, and Amiga ProTracker is where
                the sliding command arrived.
        """
        raise ValueError(
            f"a volume slide of up {up} and down {down} needs a command this format numbers none for, "
            "which Amiga ProTracker spells with A"
        )

    def set_panning(self, position: int) -> Effect:
        """Place the channel on the stereo field, on the shared 0..255 scale.

        Raises:
            ValueError: always. The machine this format was written on wires its four channels to fixed
                sides, so a song states its stereo field by which channel it plays a voice on.
        """
        raise ValueError(
            f"panning {position} needs a command this format numbers none for, "
            "and this format's channels are wired to the sides they play on"
        )


ST_EFFECTS: Final = STEffects()

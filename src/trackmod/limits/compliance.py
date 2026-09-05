from enum import StrEnum, unique


@unique
class Compliance(StrEnum):
    """How strictly a module is held: which of a format's three ceilings its values must land inside.

    Every format has three, and they are rarely the same one. ``CANONICAL`` is what the tracker the
    format names honoured in its own editor. ``EXTENDED`` is what the players descended from it read,
    which is what a module needs to play. ``STRUCTURAL`` is what the record layout physically holds,
    past which a value has no bytes to sit in.
    """

    CANONICAL = "canonical"
    EXTENDED = "extended"
    STRUCTURAL = "structural"

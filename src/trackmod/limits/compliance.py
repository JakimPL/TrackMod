from enum import StrEnum, unique


@unique
class Compliance(StrEnum):
    """How strictly a module is held: which of a format's three ceilings its values must land inside.

    Every format has three ceilings, and they are rarely the same one:

    * ``CANONICAL`` is what the tracker the format names allowed in its own editor. Write to this level
      for a module that has to open in that tracker.
    * ``EXTENDED`` is what the players descended from it read. Write to this level for a module that
      has to play, in OpenMPT or anything descended from it.
    * ``STRUCTURAL`` is what the record layout physically holds, past which a value has no bytes to sit
      in. Reading holds a file to this level, because a file that exists is evidence its values fit.

    The limits reference states every bound behind these.
    """

    CANONICAL = "canonical"
    EXTENDED = "extended"
    STRUCTURAL = "structural"

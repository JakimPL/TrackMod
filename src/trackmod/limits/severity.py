from enum import StrEnum, unique


@unique
class Severity(StrEnum):
    """Which of a format's three ceilings a value passed, which is what says who will read it back.

    A ``COMPLIANCE`` value is one the tracker the format names would refuse while its descendants play
    it. An ``EXTENDED`` value is one those descendants refuse too, though the bytes still hold it. A
    ``STRUCTURAL`` value has no bytes to sit in at all.
    """

    COMPLIANCE = "compliance"
    EXTENDED = "extended"
    STRUCTURAL = "structural"

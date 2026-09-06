import pytest

from trackmod.module.provenance import Evidence, Provenance


def test_a_statement_naming_a_program_reads_as_that_program() -> None:
    stated = Provenance(evidence=Evidence.NAMED, stated="MilkyTracker", tracker="MilkyTracker")

    assert str(stated) == "MilkyTracker"


def test_a_statement_naming_a_program_this_library_reads_none_of_shows_what_it_holds() -> None:
    # A number no program claims still says what the file states, so a caller has the evidence itself.
    stated = Provenance(evidence=Evidence.NUMBERED, stated="0xF000", tracker=None)

    assert str(stated) == "0xF000"


def test_a_statement_says_which_kind_of_evidence_carried_it() -> None:
    # A name a file spells reaches the program; a tag reaches only the family that settled the layout.
    named = Provenance(evidence=Evidence.NAMED, stated="OpenMPT 1.26", tracker="OpenMPT 1.26")
    tagged = Provenance(evidence=Evidence.TAGGED, stated="M.K.", tracker="Amiga ProTracker")

    assert named.evidence is Evidence.NAMED
    assert tagged.evidence is Evidence.TAGGED


def test_a_statement_holds_still() -> None:
    stated = Provenance(evidence=Evidence.SIGNED, stated="TMOD", tracker="TrackMod")

    with pytest.raises(ValueError, match="frozen"):
        stated.tracker = "something else"  # type: ignore[misc]

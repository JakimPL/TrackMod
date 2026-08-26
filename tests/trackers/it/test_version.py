from dataclasses import dataclass

import pytest

from trackmod.trackers.it.spec.identity import CREATED_WITH
from trackmod.trackers.it.version import TRACKER_NUMBERS, Tracker, version, wrote


@dataclass(frozen=True)
class StatedVersion:
    created_with: int
    tracker: Tracker | None
    version: int
    name: str


STATED = (
    StatedVersion(created_with=CREATED_WITH, tracker=Tracker.IMPULSE_TRACKER, version=0x214, name="it-2.14"),
    StatedVersion(created_with=0x0217, tracker=Tracker.IMPULSE_TRACKER, version=0x217, name="it-2.17"),
    StatedVersion(created_with=0x1234, tracker=Tracker.SCHISM_TRACKER, version=0x234, name="schism"),
    StatedVersion(created_with=0x5132, tracker=Tracker.OPEN_MPT, version=0x132, name="openmpt-1.32"),
    StatedVersion(created_with=0x7FFF, tracker=None, version=0xFFF, name="unclaimed"),
)


@pytest.mark.parametrize("stated", STATED, ids=lambda stated: stated.name)
def test_a_created_with_field_names_the_program_that_wrote_a_file(stated: StatedVersion) -> None:
    assert wrote(stated.created_with) is stated.tracker
    assert version(stated.created_with) == stated.version


def test_every_program_this_library_names_takes_a_number_of_its_own() -> None:
    # Two programs sharing a number would read one file as the other's, so each claims one alone.
    assert set(TRACKER_NUMBERS.values()) == set(Tracker)
    assert len(TRACKER_NUMBERS) == len(Tracker)


def test_a_version_states_nothing_about_which_program_wrote_it() -> None:
    # The version bits are each program's own spelling, so they are answered as the field holds them.
    assert version(0x5132) == version(0x0132) == 0x132

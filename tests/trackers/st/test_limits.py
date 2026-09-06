import pytest

from trackmod.core.songs.song import Song
from trackmod.limits.capability import Capability
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import LimitError
from trackmod.trackers.amiga.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.amiga.spec.periods import CANONICAL_MAX_NOTE, CANONICAL_MIN_NOTE
from trackmod.trackers.amiga.spec.ranges import PATTERN_ROWS
from trackmod.trackers.st.limits import st_limits
from trackmod.trackers.st.module import STModule
from trackmod.trackers.st.spec.ranges import CHANNELS, MAX_SAMPLES

WIDER = 8


@pytest.mark.parametrize("compliance", list(Compliance))
def test_the_width_this_format_holds_is_the_one_its_machine_played(compliance: Compliance) -> None:
    # The header states no width anywhere, so there is no wider reading for a later player to reach:
    # every module of this format plays the four channels the machine had.
    bound = st_limits(compliance).bound(Capability.CHANNELS)
    assert bound.minimum == bound.maximum == CHANNELS


@pytest.mark.parametrize("compliance", list(Compliance))
def test_the_clock_this_format_starts_on_is_the_only_one_it_states(compliance: Compliance) -> None:
    limits = st_limits(compliance)
    assert limits.bound(Capability.SPEED).maximum == DEFAULT_SPEED
    assert limits.bound(Capability.TEMPO).maximum == DEFAULT_TEMPO
    assert limits.bound(Capability.PATTERN_ROWS).minimum == PATTERN_ROWS


def test_this_format_holds_half_the_slots_the_one_after_it_did() -> None:
    assert st_limits(Compliance.STRUCTURAL).bound(Capability.SAMPLES).maximum == MAX_SAMPLES
    assert MAX_SAMPLES == 15


def test_a_song_wider_than_the_machine_is_refused_at_every_level(st_song: Song) -> None:
    wide = st_song.model_copy(
        update={"channels": WIDER, "patterns": tuple(pattern.widened(WIDER) for pattern in st_song.patterns)}
    )
    for compliance in Compliance:
        (violation,) = [
            entry
            for entry in STModule.from_song(wide, compliance=compliance).violations()
            if entry.capability is Capability.CHANNELS
        ]
        assert violation.level is Compliance.STRUCTURAL

    with pytest.raises(LimitError, match="channels"):
        STModule.from_song(wide, compliance=Compliance.STRUCTURAL).to_bytes()


def test_the_three_octaves_this_format_tabulates_are_the_canonical_reach() -> None:
    canonical = st_limits(Compliance.CANONICAL).bound(Capability.NOTE)
    assert canonical.minimum == CANONICAL_MIN_NOTE
    assert canonical.maximum == CANONICAL_MAX_NOTE
    assert canonical.maximum - canonical.minimum + 1 == 36

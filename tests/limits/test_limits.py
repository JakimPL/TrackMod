import pytest

from trackmod.limits.bound import Bound
from trackmod.limits.capability import Capability
from trackmod.limits.capacity import Capacity
from trackmod.limits.checklist import Checklist
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import LimitError, require
from trackmod.limits.guard import require_range
from trackmod.limits.reach import beyond, reached
from trackmod.limits.severity import Severity
from trackmod.limits.table import Limits
from trackmod.limits.violation import Violation

CAPACITIES = {
    Capability.TEMPO: Capacity(
        canonical=Bound(minimum=32, maximum=255),
        extended=Bound(minimum=32, maximum=1000),
        structural=Bound(minimum=32, maximum=65535),
    ),
    Capability.CHANNELS: Capacity.fixed(Bound(minimum=1, maximum=64)),
}

BEYOND_CANONICAL = 441
BEYOND_EXTENDED = 2000
BEYOND_STRUCTURAL = 70000


def limits(compliance: Compliance) -> Limits:
    return Limits(compliance=compliance, capacities=CAPACITIES)


def graded(compliance: Compliance, value: int) -> Violation | None:
    return limits(compliance).check(Capability.TEMPO, value, subject="song")


@pytest.mark.parametrize("compliance", list(Compliance))
def test_a_value_inside_the_canonical_bound_passes_at_every_level(compliance: Compliance) -> None:
    assert graded(compliance, 125) is None


def test_a_value_is_graded_against_the_widest_ceiling_it_passes() -> None:
    # The widest ceiling a value passes is the one worth reporting, because passing a wide bound means
    # passing every tighter one, and the widest says who will still read the file back.
    severities = {
        BEYOND_CANONICAL: Severity.COMPLIANCE,
        BEYOND_EXTENDED: Severity.EXTENDED,
        BEYOND_STRUCTURAL: Severity.STRUCTURAL,
    }
    for value, severity in severities.items():
        violation = graded(Compliance.CANONICAL, value)
        assert violation is not None
        assert violation.severity is severity


def test_each_level_reports_the_ceilings_at_or_beyond_it() -> None:
    reported = {
        (compliance, value) for compliance in Compliance for value in severities_by_level() if graded(compliance, value)
    }
    assert reported == {
        (Compliance.CANONICAL, BEYOND_CANONICAL),
        (Compliance.CANONICAL, BEYOND_EXTENDED),
        (Compliance.CANONICAL, BEYOND_STRUCTURAL),
        (Compliance.EXTENDED, BEYOND_EXTENDED),
        (Compliance.EXTENDED, BEYOND_STRUCTURAL),
        (Compliance.STRUCTURAL, BEYOND_STRUCTURAL),
    }


def severities_by_level() -> tuple[int, ...]:
    return (BEYOND_CANONICAL, BEYOND_EXTENDED, BEYOND_STRUCTURAL)


@pytest.mark.parametrize("compliance", list(Compliance))
def test_a_value_the_field_cannot_hold_always_fails(compliance: Compliance) -> None:
    violation = graded(compliance, BEYOND_STRUCTURAL)
    assert violation is not None
    assert violation.severity is Severity.STRUCTURAL


def test_a_capability_with_no_headroom_fails_identically_at_every_level() -> None:
    graded_channels = [limits(compliance).check(Capability.CHANNELS, 65, subject="song") for compliance in Compliance]
    assert all(violation is not None and violation.severity is Severity.STRUCTURAL for violation in graded_channels)


def test_the_effective_bound_widens_with_compliance() -> None:
    reached_maxima = [limits(compliance).bound(Capability.TEMPO).maximum for compliance in Compliance]
    assert reached_maxima == [255, 1000, 65535]


def test_a_bound_escaping_the_one_that_should_contain_it_is_rejected() -> None:
    widest = Bound(minimum=32, maximum=255)
    with pytest.raises(ValueError, match="canonical"):
        Capacity(canonical=Bound(minimum=32, maximum=512), extended=widest, structural=widest)

    with pytest.raises(ValueError, match="extended"):
        Capacity(canonical=widest, extended=Bound(minimum=32, maximum=512), structural=widest)


def test_an_empty_bound_is_rejected() -> None:
    with pytest.raises(ValueError):
        Bound(minimum=10, maximum=9)


def test_a_song_breaking_nothing_reaches_the_tightest_level() -> None:
    assert reached(()) is Compliance.CANONICAL


def test_a_song_reaches_the_level_above_the_widest_ceiling_it_passes() -> None:
    for value, level in (
        (BEYOND_CANONICAL, Compliance.EXTENDED),
        (BEYOND_EXTENDED, Compliance.STRUCTURAL),
        (BEYOND_STRUCTURAL, Compliance.STRUCTURAL),
    ):
        violation = graded(Compliance.CANONICAL, value)
        assert violation is not None
        assert reached((violation,)) is level


def test_only_the_ceilings_at_or_past_a_level_are_what_holding_to_it_refuses() -> None:
    passed = tuple(
        violation for value in severities_by_level() if (violation := graded(Compliance.CANONICAL, value)) is not None
    )
    assert len(beyond(passed, Compliance.CANONICAL)) == 3
    assert len(beyond(passed, Compliance.EXTENDED)) == 2
    assert len(beyond(passed, Compliance.STRUCTURAL)) == 1


def test_a_checklist_collects_every_problem_before_raising() -> None:
    checklist = Checklist(limits(Compliance.CANONICAL))
    checklist.check(Capability.TEMPO, BEYOND_CANONICAL, subject="song")
    checklist.check(Capability.CHANNELS, 128, subject="song")
    checklist.check(Capability.TEMPO, 125, subject="song")
    assert len(checklist.violations) == 2
    with pytest.raises(LimitError) as error:
        require(checklist.violations)

    assert error.value.violations == checklist.violations


def test_an_empty_checklist_raises_nothing() -> None:
    require(Checklist(limits(Compliance.CANONICAL)).violations)


@pytest.mark.parametrize(("value", "clamped"), [(-5, 0), (0, 0), (32, 32), (64, 64), (100, 64)])
def test_clamping_moves_a_value_to_the_nearer_end_of_the_range(value: int, clamped: int) -> None:
    assert Bound(minimum=0, maximum=64).clamp(value) == clamped


def test_a_bound_states_how_many_values_it_holds() -> None:
    assert Bound(minimum=0, maximum=64).room == 65
    assert Bound(minimum=7, maximum=7).room == 1


def test_a_guarded_value_inside_its_bound_passes_through() -> None:
    bound = Bound(minimum=0, maximum=15)
    assert require_range(15, bound=bound, subject="delay") == 15
    with pytest.raises(ValueError):
        require_range(16, bound=bound, subject="delay")

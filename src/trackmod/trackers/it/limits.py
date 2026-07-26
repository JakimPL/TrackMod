from trackmod.limits.compliance import Compliance
from trackmod.limits.table import Limits
from trackmod.trackers.it.spec.capacities import CAPACITIES


def it_limits(compliance: Compliance) -> Limits:
    """The bounds an Impulse Tracker module is held to at one compliance level."""
    return Limits(compliance=compliance, capacities=CAPACITIES)

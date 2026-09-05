from trackmod.limits.compliance import Compliance
from trackmod.limits.table import Limits
from trackmod.trackers.mod.spec.capacities import CAPACITIES


def mod_limits(compliance: Compliance) -> Limits:
    """The bounds an Amiga ProTracker module is held to at one compliance level."""
    return Limits(compliance=compliance, capacities=CAPACITIES)

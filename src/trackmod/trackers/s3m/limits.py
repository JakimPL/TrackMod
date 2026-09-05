from trackmod.limits.compliance import Compliance
from trackmod.limits.table import Limits
from trackmod.trackers.s3m.spec.capacities import CAPACITIES


def s3m_limits(compliance: Compliance) -> Limits:
    """The bounds a Scream Tracker 3 module is held to at one compliance level."""
    return Limits(compliance=compliance, capacities=CAPACITIES)

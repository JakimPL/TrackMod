from trackmod.limits.compliance import Compliance
from trackmod.limits.table import Limits
from trackmod.trackers.st.spec.capacities import CAPACITIES


def st_limits(compliance: Compliance) -> Limits:
    """The bounds a fifteen-sample Soundtracker module is held to at one compliance level."""
    return Limits(compliance=compliance, capacities=CAPACITIES)

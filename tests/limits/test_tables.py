from collections.abc import Callable

import pytest

from trackmod.limits.capability import Capability
from trackmod.limits.capacity import Capacity
from trackmod.limits.compliance import Compliance
from trackmod.limits.table import Limits
from trackmod.trackers.it.limits import it_limits
from trackmod.trackers.mod.limits import mod_limits
from trackmod.trackers.s3m.limits import s3m_limits
from trackmod.trackers.xm.limits import xm_limits

# Every ceiling below is written out as the number a tracker holds rather than imported from the
# constant that states it, so moving one takes two edits: the specification, and the claim about the
# tracker it answers to. The rows are the table `docs/limits.md` publishes, cell for cell.

IMPULSE_TRACKER = {
    Capability.CHANNELS: "1..64 / 1..127 / 1..127",
    Capability.PATTERNS: "0..200 / 0..240 / 0..254",
    Capability.ORDERS: "0..256 / 0..65535 / 0..65535",
    Capability.PATTERN_ROWS: "32..200 / 1..1024 / 1..65535",
    Capability.PATTERN_BYTES: "0..65535",
    Capability.INSTRUMENTS: "0..99 / 0..255 / 0..255",
    Capability.SAMPLES: "0..99 / 0..255 / 0..255",
    Capability.SAMPLES_PER_INSTRUMENT: "0..255",
    Capability.SAMPLE_FRAMES: "0..4294967295",
    Capability.SAMPLE_RATE: "1..9999999 / 1..4294967295 / 1..4294967295",
    Capability.SAMPLE_VOLUME: "0..64",
    Capability.SAMPLE_GAIN: "0..64",
    Capability.INSTRUMENT_VOLUME: "0..128",
    Capability.ENVELOPE_POINTS: "1..25",
    Capability.ENVELOPE_VALUE: "-128..127",
    Capability.ENVELOPE_TICK: "0..65535",
    Capability.FADEOUT: "0..128 / 0..65535 / 0..65535",
    Capability.NOTE: "0..119",
    Capability.TEMPO: "32..255",
    Capability.SPEED: "1..255",
    Capability.VOLUME_COMMAND: "0..9",
    Capability.VOLUME_PANNING: "0..64",
    Capability.SONG_VOLUME: "0..128 / 0..128 / 0..255",
    Capability.MIX_VOLUME: "0..128 / 0..128 / 0..255",
    Capability.MESSAGE_BYTES: "0..8000 / 0..65535 / 0..65535",
}

FAST_TRACKER = {
    Capability.CHANNELS: "1..32 / 1..127 / 1..65535",
    Capability.PATTERNS: "0..256 / 0..256 / 0..65535",
    Capability.ORDERS: "0..256 / 0..256 / 0..65535",
    Capability.PATTERN_ROWS: "1..256 / 1..1024 / 1..65535",
    Capability.PATTERN_BYTES: "0..65535",
    Capability.INSTRUMENTS: "0..128 / 0..255 / 0..255",
    Capability.SAMPLES: "0..2048 / 0..65025 / 0..65025",
    Capability.SAMPLES_PER_INSTRUMENT: "0..16 / 0..255 / 0..255",
    Capability.SAMPLE_FRAMES: "0..4294967295",
    Capability.SAMPLE_BYTES: "0..4294967295",
    Capability.SAMPLE_RATE: "10..25662141",
    Capability.SAMPLE_VOLUME: "0..64",
    Capability.SAMPLE_GAIN: "64..64",
    Capability.INSTRUMENT_VOLUME: "128..128",
    Capability.ENVELOPE_POINTS: "1..12",
    Capability.ENVELOPE_VALUE: "0..64",
    Capability.ENVELOPE_TICK: "0..65535",
    Capability.FADEOUT: "0..4095 / 0..65535 / 0..65535",
    Capability.NOTE: "0..95",
    Capability.TEMPO: "32..255 / 32..1000 / 1..65535",
    Capability.SPEED: "1..31 / 1..65535 / 1..65535",
    Capability.VOLUME_COMMAND: "0..15",
    Capability.VOLUME_PANNING: "0..15",
}

PROTRACKER = {
    Capability.CHANNELS: "4..4 / 1..32 / 1..99",
    Capability.PATTERNS: "0..64 / 0..256 / 0..256",
    Capability.ORDERS: "0..128",
    Capability.PATTERN_ROWS: "64..64",
    Capability.SAMPLES: "0..31",
    Capability.SAMPLE_FRAMES: "0..131070",
    Capability.SAMPLE_BYTES: "0..131070",
    Capability.SAMPLE_RATE: "7893..8795",
    Capability.SAMPLE_VOLUME: "0..64",
    Capability.SAMPLE_GAIN: "64..64",
    Capability.NOTE: "48..83 / 21..119 / 21..119",
    Capability.TEMPO: "125..125",
    Capability.SPEED: "6..6",
}

SCREAM_TRACKER = {
    Capability.CHANNELS: "1..16 / 1..32 / 1..32",
    Capability.PATTERNS: "0..100 / 0..254 / 0..254",
    Capability.ORDERS: "0..255 / 0..65535 / 0..65535",
    Capability.PATTERN_ROWS: "64..64",
    Capability.PATTERN_BYTES: "0..65535",
    Capability.BLOCK_OFFSET: "0..1048560",
    Capability.SAMPLES: "0..99 / 0..255 / 0..255",
    Capability.SAMPLE_FRAMES: "0..64000 / 0..4294967295 / 0..4294967295",
    Capability.SAMPLE_BYTES: "0..64000 / 0..17179869180 / 0..17179869180",
    Capability.SAMPLE_OFFSET: "0..268435440",
    Capability.SAMPLE_RATE: "1..65535 / 1..4294967295 / 1..4294967295",
    Capability.SAMPLE_VOLUME: "0..64",
    Capability.SAMPLE_GAIN: "64..64",
    Capability.NOTE: "12..107 / 12..119 / 12..119",
    Capability.TEMPO: "32..255",
    Capability.SPEED: "1..255",
    Capability.VOLUME_PANNING: "0..64",
    Capability.SONG_VOLUME: "0..64 / 0..64 / 0..255",
    Capability.MIX_VOLUME: "0..127",
}

PUBLISHED = (
    ("it", it_limits(Compliance.CANONICAL), IMPULSE_TRACKER),
    ("xm", xm_limits(Compliance.CANONICAL), FAST_TRACKER),
    ("mod", mod_limits(Compliance.CANONICAL), PROTRACKER),
    ("s3m", s3m_limits(Compliance.CANONICAL), SCREAM_TRACKER),
)

TABLES = [(limits, table) for _, limits, table in PUBLISHED]
NAMES = [name for name, _, _ in PUBLISHED]

LIMIT_BUILDERS = (it_limits, xm_limits, mod_limits, s3m_limits)


def stated(capacity: Capacity) -> str:
    """The ceilings a capacity holds, spelled the way the published table spells them.

    Three bounds separated by slashes are the canonical, extended and structural ones; a single bound
    is a field with the same room at every level.
    """
    bounds = (capacity.canonical, capacity.extended, capacity.structural)
    return str(bounds[0]) if len(set(bounds)) == 1 else " / ".join(str(bound) for bound in bounds)


@pytest.mark.parametrize(("limits", "published"), TABLES, ids=NAMES)
def test_each_format_states_the_ceilings_its_trackers_hold(limits: Limits, published: dict[Capability, str]) -> None:
    assert {capability: stated(capacity) for capability, capacity in limits.capacities.items()} == published


@pytest.mark.parametrize("build", LIMIT_BUILDERS, ids=NAMES)
@pytest.mark.parametrize("compliance", list(Compliance))
def test_a_value_on_a_ceiling_passes_where_the_next_one_along_is_reported(
    build: Callable[[Compliance], Limits],
    compliance: Compliance,
) -> None:
    # A bound states two facts, and a table that got either end wrong grades the same as one that got
    # both right unless the values either side of it are asked about.
    limits = build(compliance)
    for capability in limits.capacities:
        bound = limits.bound(capability)
        assert limits.check(capability, bound.minimum, subject="song") is None
        assert limits.check(capability, bound.maximum, subject="song") is None
        assert limits.check(capability, bound.minimum - 1, subject="song") is not None
        assert limits.check(capability, bound.maximum + 1, subject="song") is not None

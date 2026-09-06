from typing import Final

from trackmod.limits.bound import Bound
from trackmod.limits.capability import Capability
from trackmod.limits.capacity import Capacity
from trackmod.spec.levels import MAX_VOLUME
from trackmod.trackers.amiga.spec.defaults import DEFAULT_SPEED, DEFAULT_TEMPO
from trackmod.trackers.amiga.spec.periods import (
    CANONICAL_MAX_NOTE,
    CANONICAL_MIN_NOTE,
    MAX_NOTE,
    MIN_NOTE,
)
from trackmod.trackers.amiga.spec.ranges import (
    MAX_ORDERS,
    MAX_SAMPLE_BYTES,
    MAX_SAMPLE_FRAMES,
    MAX_SAMPLE_RATE,
    MIN_SAMPLE_RATE,
    PATTERN_ROWS,
)
from trackmod.trackers.mod.spec.ranges import (
    CANONICAL_CHANNELS,
    EXTENDED_MAX_CHANNELS,
    EXTENDED_MAX_PATTERNS,
    EXTENDED_MIN_CHANNELS,
    MAX_SAMPLES,
    STRUCTURAL_MAX_CHANNELS,
    TAGGED_MAX_PATTERNS,
)

CAPACITIES: Final = {
    Capability.CHANNELS: Capacity(
        canonical=Bound(minimum=CANONICAL_CHANNELS, maximum=CANONICAL_CHANNELS),
        extended=Bound(minimum=EXTENDED_MIN_CHANNELS, maximum=EXTENDED_MAX_CHANNELS),
        structural=Bound(minimum=EXTENDED_MIN_CHANNELS, maximum=STRUCTURAL_MAX_CHANNELS),
    ),
    Capability.PATTERNS: Capacity(
        canonical=Bound(minimum=0, maximum=TAGGED_MAX_PATTERNS),
        extended=Bound(minimum=0, maximum=EXTENDED_MAX_PATTERNS),
        structural=Bound(minimum=0, maximum=EXTENDED_MAX_PATTERNS),
    ),
    Capability.ORDERS: Capacity.fixed(Bound(minimum=0, maximum=MAX_ORDERS)),
    Capability.PATTERN_ROWS: Capacity.fixed(Bound(minimum=PATTERN_ROWS, maximum=PATTERN_ROWS)),
    Capability.SAMPLES: Capacity.fixed(Bound(minimum=0, maximum=MAX_SAMPLES)),
    Capability.SAMPLE_FRAMES: Capacity.fixed(Bound(minimum=0, maximum=MAX_SAMPLE_FRAMES)),
    Capability.SAMPLE_BYTES: Capacity.fixed(Bound(minimum=0, maximum=MAX_SAMPLE_BYTES)),
    Capability.SAMPLE_RATE: Capacity.fixed(Bound(minimum=MIN_SAMPLE_RATE, maximum=MAX_SAMPLE_RATE)),
    Capability.SAMPLE_VOLUME: Capacity.fixed(Bound(minimum=0, maximum=MAX_VOLUME)),
    Capability.SAMPLE_GAIN: Capacity.fixed(Bound(minimum=MAX_VOLUME, maximum=MAX_VOLUME)),
    Capability.NOTE: Capacity(
        canonical=Bound(minimum=CANONICAL_MIN_NOTE, maximum=CANONICAL_MAX_NOTE),
        extended=Bound(minimum=MIN_NOTE, maximum=MAX_NOTE),
        structural=Bound(minimum=MIN_NOTE, maximum=MAX_NOTE),
    ),
    Capability.TEMPO: Capacity.fixed(Bound(minimum=DEFAULT_TEMPO, maximum=DEFAULT_TEMPO)),
    Capability.SPEED: Capacity.fixed(Bound(minimum=DEFAULT_SPEED, maximum=DEFAULT_SPEED)),
}

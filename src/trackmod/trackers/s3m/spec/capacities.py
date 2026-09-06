from typing import Final

from trackmod.limits.bound import Bound
from trackmod.limits.capability import Capability
from trackmod.limits.capacity import Capacity
from trackmod.spec.levels import MAX_VOLUME
from trackmod.spec.width import WORD_MAX
from trackmod.trackers.s3m.spec.keys import (
    CANONICAL_MAX_NOTE,
    CANONICAL_MIN_NOTE,
    MAX_NOTE,
    MIN_NOTE,
)
from trackmod.trackers.s3m.spec.ranges import (
    CANONICAL_MAX_CHANNELS,
    CANONICAL_MAX_ORDERS,
    CANONICAL_MAX_PATTERNS,
    CANONICAL_MAX_SAMPLE_BYTES,
    CANONICAL_MAX_SAMPLE_FRAMES,
    CANONICAL_MAX_SAMPLE_RATE,
    CANONICAL_MAX_SAMPLES,
    MAX_GLOBAL_VOLUME,
    MAX_MIX_VOLUME,
    MAX_SAMPLE_VOLUME,
    MAX_SPEED,
    MAX_TEMPO,
    MAX_VOLUME_PANNING,
    MIN_CHANNEL_COUNT,
    MIN_SPEED,
    MIN_TEMPO,
    PATTERN_ROWS,
    STRUCTURAL_MAX_CHANNELS,
    STRUCTURAL_MAX_GLOBAL_VOLUME,
    STRUCTURAL_MAX_ORDERS,
    STRUCTURAL_MAX_PATTERNS,
    STRUCTURAL_MAX_SAMPLE_BYTES,
    STRUCTURAL_MAX_SAMPLE_FRAMES,
    STRUCTURAL_MAX_SAMPLE_RATE,
    STRUCTURAL_MAX_SAMPLES,
)

CAPACITIES: Final = {
    Capability.CHANNELS: Capacity(
        canonical=Bound(minimum=MIN_CHANNEL_COUNT, maximum=CANONICAL_MAX_CHANNELS),
        extended=Bound(minimum=MIN_CHANNEL_COUNT, maximum=STRUCTURAL_MAX_CHANNELS),
        structural=Bound(minimum=MIN_CHANNEL_COUNT, maximum=STRUCTURAL_MAX_CHANNELS),
    ),
    Capability.PATTERNS: Capacity(
        canonical=Bound(minimum=0, maximum=CANONICAL_MAX_PATTERNS),
        extended=Bound(minimum=0, maximum=STRUCTURAL_MAX_PATTERNS),
        structural=Bound(minimum=0, maximum=STRUCTURAL_MAX_PATTERNS),
    ),
    Capability.ORDERS: Capacity(
        canonical=Bound(minimum=0, maximum=CANONICAL_MAX_ORDERS),
        extended=Bound(minimum=0, maximum=STRUCTURAL_MAX_ORDERS),
        structural=Bound(minimum=0, maximum=STRUCTURAL_MAX_ORDERS),
    ),
    Capability.PATTERN_ROWS: Capacity.fixed(Bound(minimum=PATTERN_ROWS, maximum=PATTERN_ROWS)),
    Capability.PATTERN_BYTES: Capacity.fixed(Bound(minimum=0, maximum=WORD_MAX)),
    Capability.SAMPLES: Capacity(
        canonical=Bound(minimum=0, maximum=CANONICAL_MAX_SAMPLES),
        extended=Bound(minimum=0, maximum=STRUCTURAL_MAX_SAMPLES),
        structural=Bound(minimum=0, maximum=STRUCTURAL_MAX_SAMPLES),
    ),
    Capability.SAMPLE_FRAMES: Capacity(
        canonical=Bound(minimum=0, maximum=CANONICAL_MAX_SAMPLE_FRAMES),
        extended=Bound(minimum=0, maximum=STRUCTURAL_MAX_SAMPLE_FRAMES),
        structural=Bound(minimum=0, maximum=STRUCTURAL_MAX_SAMPLE_FRAMES),
    ),
    Capability.SAMPLE_BYTES: Capacity(
        canonical=Bound(minimum=0, maximum=CANONICAL_MAX_SAMPLE_BYTES),
        extended=Bound(minimum=0, maximum=STRUCTURAL_MAX_SAMPLE_BYTES),
        structural=Bound(minimum=0, maximum=STRUCTURAL_MAX_SAMPLE_BYTES),
    ),
    Capability.SAMPLE_RATE: Capacity(
        canonical=Bound(minimum=1, maximum=CANONICAL_MAX_SAMPLE_RATE),
        extended=Bound(minimum=1, maximum=STRUCTURAL_MAX_SAMPLE_RATE),
        structural=Bound(minimum=1, maximum=STRUCTURAL_MAX_SAMPLE_RATE),
    ),
    Capability.SAMPLE_VOLUME: Capacity.fixed(Bound(minimum=0, maximum=MAX_SAMPLE_VOLUME)),
    Capability.SAMPLE_GAIN: Capacity.fixed(Bound(minimum=MAX_VOLUME, maximum=MAX_VOLUME)),
    Capability.NOTE: Capacity(
        canonical=Bound(minimum=CANONICAL_MIN_NOTE, maximum=CANONICAL_MAX_NOTE),
        extended=Bound(minimum=MIN_NOTE, maximum=MAX_NOTE),
        structural=Bound(minimum=MIN_NOTE, maximum=MAX_NOTE),
    ),
    Capability.TEMPO: Capacity.fixed(Bound(minimum=MIN_TEMPO, maximum=MAX_TEMPO)),
    Capability.SPEED: Capacity.fixed(Bound(minimum=MIN_SPEED, maximum=MAX_SPEED)),
    Capability.VOLUME_PANNING: Capacity.fixed(Bound(minimum=0, maximum=MAX_VOLUME_PANNING)),
    Capability.SONG_VOLUME: Capacity(
        canonical=Bound(minimum=0, maximum=MAX_GLOBAL_VOLUME),
        extended=Bound(minimum=0, maximum=MAX_GLOBAL_VOLUME),
        structural=Bound(minimum=0, maximum=STRUCTURAL_MAX_GLOBAL_VOLUME),
    ),
    Capability.MIX_VOLUME: Capacity.fixed(Bound(minimum=0, maximum=MAX_MIX_VOLUME)),
}

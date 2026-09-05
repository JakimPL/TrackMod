from typing import Final

from trackmod.limits.bound import Bound
from trackmod.limits.capability import Capability
from trackmod.limits.capacity import Capacity
from trackmod.spec.grid import MIN_ROWS
from trackmod.spec.levels import MAX_PANNING, MAX_VOLUME
from trackmod.spec.pitch import NOTE_COUNT
from trackmod.spec.width import (
    BYTE_MAX,
    DOUBLE_WORD_MAX,
    SIGNED_BYTE_MAX,
    SIGNED_BYTE_MIN,
    WORD_MAX,
)
from trackmod.trackers.it.spec.ranges import (
    CANONICAL_MAX_CHANNELS,
    CANONICAL_MAX_FADEOUT,
    CANONICAL_MAX_INSTRUMENTS,
    CANONICAL_MAX_MESSAGE_BYTES,
    CANONICAL_MAX_ORDERS,
    CANONICAL_MAX_SAMPLES,
    CANONICAL_MIN_ROWS,
    EXTENDED_MAX_CHANNELS,
    EXTENDED_MAX_PATTERNS,
    EXTENDED_MAX_ROWS,
    MAX_C5_SPEED,
    MAX_GLOBAL_VOLUME,
    MAX_MIX_VOLUME,
    MAX_PATTERNS,
    MAX_ROWS,
    MAX_SPEED,
    MAX_TEMPO,
    MAX_VOLUME_COMMAND,
    MAX_VOLUME_PANNING,
    MIN_SPEED,
    MIN_TEMPO,
    STRUCTURAL_MAX_CHANNELS,
    STRUCTURAL_MAX_FADEOUT,
    STRUCTURAL_MAX_INSTRUMENTS,
    STRUCTURAL_MAX_MESSAGE_BYTES,
    STRUCTURAL_MAX_ORDERS,
    STRUCTURAL_MAX_PATTERNS,
    STRUCTURAL_MAX_ROWS,
    STRUCTURAL_MAX_SAMPLES,
)
from trackmod.trackers.it.spec.sizes import ENVELOPE_NODES

CAPACITIES: Final = {
    Capability.CHANNELS: Capacity(
        canonical=Bound(minimum=1, maximum=CANONICAL_MAX_CHANNELS),
        extended=Bound(minimum=1, maximum=EXTENDED_MAX_CHANNELS),
        structural=Bound(minimum=1, maximum=STRUCTURAL_MAX_CHANNELS),
    ),
    Capability.PATTERNS: Capacity(
        canonical=Bound(minimum=0, maximum=MAX_PATTERNS),
        extended=Bound(minimum=0, maximum=EXTENDED_MAX_PATTERNS),
        structural=Bound(minimum=0, maximum=STRUCTURAL_MAX_PATTERNS),
    ),
    Capability.ORDERS: Capacity(
        canonical=Bound(minimum=0, maximum=CANONICAL_MAX_ORDERS),
        extended=Bound(minimum=0, maximum=STRUCTURAL_MAX_ORDERS),
        structural=Bound(minimum=0, maximum=STRUCTURAL_MAX_ORDERS),
    ),
    Capability.PATTERN_ROWS: Capacity(
        canonical=Bound(minimum=CANONICAL_MIN_ROWS, maximum=MAX_ROWS),
        extended=Bound(minimum=MIN_ROWS, maximum=EXTENDED_MAX_ROWS),
        structural=Bound(minimum=MIN_ROWS, maximum=STRUCTURAL_MAX_ROWS),
    ),
    Capability.PATTERN_BYTES: Capacity.fixed(Bound(minimum=0, maximum=WORD_MAX)),
    Capability.INSTRUMENTS: Capacity(
        canonical=Bound(minimum=0, maximum=CANONICAL_MAX_INSTRUMENTS),
        extended=Bound(minimum=0, maximum=STRUCTURAL_MAX_INSTRUMENTS),
        structural=Bound(minimum=0, maximum=STRUCTURAL_MAX_INSTRUMENTS),
    ),
    Capability.SAMPLES: Capacity(
        canonical=Bound(minimum=0, maximum=CANONICAL_MAX_SAMPLES),
        extended=Bound(minimum=0, maximum=STRUCTURAL_MAX_SAMPLES),
        structural=Bound(minimum=0, maximum=STRUCTURAL_MAX_SAMPLES),
    ),
    Capability.SAMPLES_PER_INSTRUMENT: Capacity.fixed(Bound(minimum=0, maximum=BYTE_MAX)),
    Capability.SAMPLE_FRAMES: Capacity.fixed(Bound(minimum=0, maximum=DOUBLE_WORD_MAX)),
    Capability.SAMPLE_RATE: Capacity.fixed(Bound(minimum=1, maximum=MAX_C5_SPEED)),
    Capability.SAMPLE_VOLUME: Capacity.fixed(Bound(minimum=0, maximum=MAX_VOLUME)),
    Capability.SAMPLE_GAIN: Capacity.fixed(Bound(minimum=0, maximum=MAX_VOLUME)),
    Capability.INSTRUMENT_VOLUME: Capacity.fixed(Bound(minimum=0, maximum=MAX_GLOBAL_VOLUME)),
    Capability.ENVELOPE_POINTS: Capacity.fixed(Bound(minimum=1, maximum=ENVELOPE_NODES)),
    Capability.ENVELOPE_VALUE: Capacity.fixed(Bound(minimum=SIGNED_BYTE_MIN, maximum=SIGNED_BYTE_MAX)),
    Capability.ENVELOPE_TICK: Capacity.fixed(Bound(minimum=0, maximum=WORD_MAX)),
    Capability.FADEOUT: Capacity(
        canonical=Bound(minimum=0, maximum=CANONICAL_MAX_FADEOUT),
        extended=Bound(minimum=0, maximum=STRUCTURAL_MAX_FADEOUT),
        structural=Bound(minimum=0, maximum=STRUCTURAL_MAX_FADEOUT),
    ),
    Capability.NOTE: Capacity.fixed(Bound(minimum=0, maximum=NOTE_COUNT - 1)),
    Capability.TEMPO: Capacity.fixed(Bound(minimum=MIN_TEMPO, maximum=MAX_TEMPO)),
    Capability.SPEED: Capacity.fixed(Bound(minimum=MIN_SPEED, maximum=MAX_SPEED)),
    Capability.VOLUME: Capacity.fixed(Bound(minimum=0, maximum=MAX_VOLUME)),
    Capability.VOLUME_COMMAND: Capacity.fixed(Bound(minimum=0, maximum=MAX_VOLUME_COMMAND)),
    Capability.VOLUME_PANNING: Capacity.fixed(Bound(minimum=0, maximum=MAX_VOLUME_PANNING)),
    Capability.SONG_VOLUME: Capacity.fixed(Bound(minimum=0, maximum=MAX_GLOBAL_VOLUME)),
    Capability.MIX_VOLUME: Capacity.fixed(Bound(minimum=0, maximum=MAX_MIX_VOLUME)),
    Capability.MESSAGE_BYTES: Capacity(
        canonical=Bound(minimum=0, maximum=CANONICAL_MAX_MESSAGE_BYTES),
        extended=Bound(minimum=0, maximum=STRUCTURAL_MAX_MESSAGE_BYTES),
        structural=Bound(minimum=0, maximum=STRUCTURAL_MAX_MESSAGE_BYTES),
    ),
    Capability.PANNING: Capacity.fixed(Bound(minimum=0, maximum=MAX_PANNING)),
}

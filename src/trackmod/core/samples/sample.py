from __future__ import annotations

from typing import Final

import numpy as np
from pydantic import BaseModel, model_validator

from trackmod.core.samples.depth import DEFAULT_DEPTH, BitDepth
from trackmod.core.samples.loop import Loop
from trackmod.core.samples.vibrato import NO_VIBRATO, Vibrato
from trackmod.schema.array import Waveform
from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Panning, Rate, Volume
from trackmod.spec.levels import MAX_VOLUME

MONO_CHANNELS: Final[int] = 1
STEREO_CHANNELS: Final[int] = 2


class Sample(BaseModel):
    """One stored waveform and how a tracker should sound it.

    ``pcm`` is float in ``[-1, 1]`` and ``rate`` is the frequency in hertz at which it plays back
    unaltered. Formats reach that rate differently — one stores the frequency outright, another tunes the
    triggering key towards it — so the intent is recorded here in hertz and each writer derives its own
    encoding. A sample with no frames is a placeholder slot for a waveform a tracker will supply later.

    ``pcm`` is shaped ``(frames,)`` for a mono waveform or ``(frames, 2)`` for a stereo one, left channel
    first — the two channels of a stereo waveform share every other field below, since no format this
    library reads gives them their own loop, volume, panning or rate.

    ``volume`` is the level a cell without a volume column plays at, and ``gain`` is a fixed multiplier
    applied on top of whatever level plays. A format with no room for a per-sample multiplier bounds
    ``gain`` to full and reports anything quieter, so a caller learns that the scaling has to be baked
    into the waveform instead of being dropped in silence.

    ``filename`` and ``vibrato`` are Impulse Tracker's own DOS filename and sample-level auto-vibrato; a
    format with no room for either leaves them at their default of an empty name and no vibrato.
    """

    model_config = FROZEN

    name: str
    pcm: Waveform
    rate: Rate
    depth: BitDepth = DEFAULT_DEPTH
    volume: Volume = MAX_VOLUME
    gain: Volume = MAX_VOLUME
    panning: Panning | None = None
    loop: Loop | None = None
    sustain_loop: Loop | None = None
    filename: str = ""
    vibrato: Vibrato = NO_VIBRATO

    @model_validator(mode="after")
    def _loops_fit(self) -> Sample:
        for loop in (self.loop, self.sustain_loop):
            if loop is not None and loop.end > self.frames:
                raise ValueError(f"sample {self.name!r} loop end {loop.end} exceeds {self.frames} frames")

        return self

    @model_validator(mode="after")
    def _channels_are_supported(self) -> Sample:
        if self.pcm.ndim == 2 and self.pcm.shape[1] != STEREO_CHANNELS:
            raise ValueError(
                f"sample {self.name!r} carries {self.pcm.shape[1]} channels, "
                "only mono or stereo waveforms are stored"
            )

        return self

    @property
    def frames(self) -> int:
        """How many frames the waveform holds, per channel."""
        return int(self.pcm.shape[0])

    @property
    def channels(self) -> int:
        """How many interleaved channels the waveform carries: 1 for mono, 2 for stereo."""
        return STEREO_CHANNELS if self.pcm.ndim == 2 else MONO_CHANNELS

    @property
    def stored_bytes(self) -> int:
        """How many bytes the waveform occupies at this sample's depth, across every channel."""
        return self.frames * self.channels * self.depth.bytes_per_frame

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Sample):
            return NotImplemented

        return self._settings(self) == self._settings(other) and np.array_equal(self.pcm, other.pcm)

    def __hash__(self) -> int:
        return hash(self._settings(self))

    @staticmethod
    def _settings(sample: Sample) -> tuple[object, ...]:
        return (
            sample.name,
            sample.rate,
            sample.depth,
            sample.volume,
            sample.gain,
            sample.panning,
            sample.loop,
            sample.sustain_loop,
            sample.frames,
            sample.channels,
            sample.filename,
            sample.vibrato,
        )

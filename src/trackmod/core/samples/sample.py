from __future__ import annotations

from typing import Final

import numpy as np
from pydantic import BaseModel, model_validator

from trackmod.core.samples.depth import DEFAULT_DEPTH, BitDepth
from trackmod.core.samples.loop import Loop
from trackmod.core.samples.vibrato import NO_VIBRATO, Vibrato
from trackmod.schema.array import Waveform
from trackmod.schema.config import FROZEN
from trackmod.schema.scalars import Panning, Rate, Transposition, Volume
from trackmod.spec.levels import MAX_VOLUME
from trackmod.spec.pitch import NO_TRANSPOSITION

MONO_CHANNELS: Final[int] = 1
STEREO_CHANNELS: Final[int] = 2


class Sample(BaseModel):
    """One recorded waveform and the settings a tracker plays it with.

    Formats reach a playback rate in different ways: one stores the frequency outright, another tunes
    the triggering key toward it. The rate is recorded here in hertz and each writer derives its own
    encoding, so one sample serves every format. A sample with no frames is a placeholder slot for a
    waveform a tracker will supply later.

    Two samples are equal when every setting and every frame match. Hashing skips the frames, because a
    numpy array cannot be hashed, so two samples differing only in their PCM share a hash.

    Args:
        name: The sample's title, as a tracker shows it.
        pcm: Float amplitudes in ``[-1, 1]``, shaped ``(frames,)`` for mono or ``(frames, 2)`` for
            stereo with the left channel first. The two channels of a stereo waveform share every other
            setting here, because no format read here gives them their own.
        rate: The frequency in hertz at which the waveform plays back unaltered.
        depth: The width one stored frame is written at. Defaults to 16-bit.
        volume: The level a cell with no volume column plays at, ``0..64``. Defaults to full.
        gain: A multiplier applied on top of whatever level plays, ``0..64``. Defaults to full. A
            format with no room for one bounds ``gain`` to full and reports anything quieter, so you
            learn the scaling has to be baked into the waveform rather than lost in silence.
        panning: A position on the shared ``0..255`` field, or ``None`` to leave it to the tracker.
        loop: The region that repeats while a note holds, or ``None``.
        sustain_loop: The region that repeats until a note is released, or ``None``.
        filename: Impulse Tracker's own DOS filename for the sample. Defaults to empty.
        vibrato: Impulse Tracker's sample-level auto-vibrato. Defaults to none.
        relative_note: FastTracker 2's stored transposition in whole semitones, kept exactly as its
            header held it. ``rate`` is already derived from it, so this is here only for reading the
            stored bytes back.
        finetune: FastTracker 2's trim on that transposition, in units of 1/128 of a semitone.

    Raises:
        ValidationError: when a loop ends past the frames the waveform holds, when ``pcm`` is neither
            mono nor two-channel stereo, or when ``rate`` is not above zero.

    Example:
        >>> import numpy as np
        >>> from trackmod import Sample
        >>> sample = Sample(name="lead", pcm=np.zeros((64, 2)), rate=44100)
        >>> sample.frames, sample.channels, sample.stored_bytes
        (64, 2, 256)
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
    relative_note: Transposition = NO_TRANSPOSITION
    finetune: Transposition = NO_TRANSPOSITION

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
            sample.relative_note,
            sample.finetune,
        )

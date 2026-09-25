# Waveforms, and saving them as audio

A `Sample` is one recorded waveform plus the way a tracker plays it: float PCM in `[-1, 1]`, the rate it
plays at its original pitch, a bit depth, two loops, and the volume, gain and panning it starts with.
See [`../reference/model.md`](../reference/model.md) for every field.

Every voice table has a `samples` attribute, whichever way its song refers to its voices, so you reach the
waveforms of any module the same way:

```python
from pathlib import Path

from trackmod import load_module

for sample in load_module(Path("song.it")).song.voices.samples:
    print(sample.name, sample.frames, sample.rate, sample.loop)
```

`sample.pcm` is a `numpy` array. Its shape is `(frames,)` for a mono waveform, or `(frames, 2)` for a stereo
one with the left channel first. You can resample it, analyze it, or pass it to anything that takes float
audio.

## Saving a waveform as a `.wav`

```python
from pathlib import Path

from trackmod import load_sample, save_sample, write_sample

save_sample(sample, Path("lead.wav"))
data = write_sample(sample)              # the same bytes, when you want them yourself
recovered = load_sample(Path("lead.wav"))
```

The result is an ordinary RIFF audio file that any editor or player opens. Next to the frames, it stores
what a tracker needs to play the sample the way the module did, in the chunks OpenMPT writes:

| Chunk | What it holds |
|---|---|
| `fmt ` | The channel count, the rate and the bit depth |
| `data` | The frames, with the channels interleaved |
| `smpl` | The pitch the waveform plays at unaltered, then the loops |
| `inst` | The root key and the range of keys the waveform answers |
| `xtra` | The volume, the gain, the panning, the auto-vibrato, and the two names |
| `LIST`/`INFO` | The title, under `INAM` |

The file stores the sustain loop first and the ordinary loop second, and that order is the only thing that
identifies each. A sample with only a sustain loop still writes two loops. The second one is empty, so the
sustain loop stays first. The loop end in the file is the last frame the loop plays. The model's own end is
exclusive, so the stored value is one lower.

## Reading one back

`load_sample` and `parse_sample` take the frames, the rate and the sample width from the audio data itself,
and everything else from the chunks a tracker adds. An ordinary `.wav` from another program carries only the
frames, so it arrives at full volume with no loop, the way a player would play it.

TrackMod reads 8-bit and 16-bit integer samples, in mono or stereo. A file in any other form is refused.

The pitch is stored as the playback rate, which is what every `.wav` reader uses. FastTracker 2 reaches its
rate through a semitone offset and a finetune value of its own. Those two values stay in the module, and the
audio file holds the rate they add up to.

## Saving every waveform in a folder

```python
from pathlib import Path

from trackmod import load_voices, save_sample

sounds = Path("sounds")
for path in Path("modules").iterdir():
    for index, sample in enumerate(load_voices(path).samples):
        save_sample(sample, sounds / f"{path.stem}-{index:02d}.wav")
```

`load_voices` reads a module and a standalone instrument file the same way, so one loop handles a folder
that holds both. See [`instruments.md`](instruments.md) for the other half: saving each instrument as a file
that a tracker opens.

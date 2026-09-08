# Waveforms, and saving them as audio

A `Sample` is one recorded waveform plus how a tracker plays it: float PCM in `[-1, 1]`, the rate it plays
back at unaltered, a bit depth, two loops, and the levels and position it starts at. See
[`../reference/model.md`](../reference/model.md) for every field.

Every voice table answers `samples`, whichever way its song addresses its voices, so the waveforms of any
module are one attribute away:

```python
from pathlib import Path

from trackmod import load_module

for sample in load_module(Path("song.it")).song.voices.samples:
    print(sample.name, sample.frames, sample.rate, sample.loop)
```

`sample.pcm` is a `numpy` array. It is shaped `(frames,)` for a mono waveform, or `(frames, 2)` for a stereo
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

The result is an ordinary RIFF audio file that any editor or player opens. Alongside the frames it stores
what a tracker needs to play the sample the way the module did, in the chunks OpenMPT writes:

| Chunk | What it holds |
|---|---|
| `fmt ` | The channel count, the rate and the bit depth |
| `data` | The frames, with the channels interleaved |
| `smpl` | The pitch the waveform plays unaltered, then the loops |
| `inst` | The root key and the range of keys the waveform answers |
| `xtra` | The volume, the gain, the panning, the auto-vibrato, and the two names |
| `LIST`/`INFO` | The title, under `INAM` |

The sustain loop is written first and the ordinary loop second, because order is all that tells the two
apart. A sample that loops over its sustain alone still writes a pair, with the second loop spanning
nothing, so the sustain stays first. A stored loop end names the last frame the region plays, which is one
below the model's own half-open end.

## Reading one back

`parse_sample` and `load_sample` read the frames, their rate and their width from the file itself, and
everything else from the chunks a tracker adds. An ordinary `.wav` from elsewhere carries only the frames,
so it arrives at full volume with no loop, which is how a player plays it.

This container reads 8-bit and 16-bit whole amplitudes, in mono or stereo. A file stating anything else is
refused by name.

The pitch travels as the rate the frames go by, which is what every reader of a `.wav` plays them at. One
format arrives at its rate through a semitone offset and a finetune trim of its own; those stay with the
module that holds them, and the audio file names the rate they reach.

## Emptying a whole folder

```python
from pathlib import Path

from trackmod import load_voices, save_sample

sounds = Path("sounds")
for path in Path("modules").iterdir():
    for index, sample in enumerate(load_voices(path).samples):
        save_sample(sample, sounds / f"{path.stem}-{index:02d}.wav")
```

`load_voices` reads a module and a standalone instrument file alike, so one loop empties a folder holding
both. See [`instruments.md`](instruments.md) for the other half: saving each instrument as a file a tracker
opens.

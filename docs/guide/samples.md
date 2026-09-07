# Waveforms, and writing them out as audio

A `Sample` is one recorded waveform and how a tracker sounds it: float PCM in `[-1, 1]`, the rate it plays
back unaltered at, a bit depth, two loops, and the levels and position it starts at. See
[`../reference/model.md`](../reference/model.md) for every field.

Every voice table answers `samples`, whichever way its song addresses its voices, so the waveforms of any
module are one attribute away:

```python
from pathlib import Path

from trackmod import load_module

for sample in load_module(Path("song.it")).song.voices.samples:
    print(sample.name, sample.frames, sample.rate, sample.loop)
```

`sample.pcm` is a `numpy` array shaped `(frames,)` for a mono waveform or `(frames, 2)` for a stereo one,
left channel first — ready to resample, analyse or feed to anything that takes float audio.

## Writing a waveform as a `.wav`

```python
from pathlib import Path

from trackmod import load_sample, save_sample, write_sample

save_sample(sample, Path("lead.wav"))
data = write_sample(sample)              # the same bytes, where you want them yourself
recovered = load_sample(Path("lead.wav"))
```

The file is an ordinary RIFF audio file: any editor or player opens it. Beside the frames it carries what
a tracker needs to sound the sample the way the module did, in the chunks OpenMPT writes, so a waveform
exported here opens in a tracker as the sample it came from.

| Chunk | What it carries |
|---|---|
| `fmt ` | The channel count, the rate and the bit depth |
| `data` | The frames, with the channels interleaved |
| `smpl` | The pitch the waveform sounds unaltered, then the loops |
| `inst` | The root key and the range of keys the waveform answers |
| `xtra` | The level, the gain, the position, the auto-vibrato, and the two names |
| `LIST`/`INFO` | The title, under `INAM` |

The sustain loop is written first and the ordinary loop second, because order is all that tells the two
apart. A sample looping over its sustain alone still states a pair, the second spanning nothing, which
keeps the sustain first. A stored loop end names the last frame the region plays, one below the model's
own half-open end, which is the single arithmetic both writers of these files agree on.

## Reading one back

`parse_sample` and `load_sample` read the frames, their rate and their width from the file itself, and
everything a tracker sounds them with from the chunks a tracker adds. An ordinary `.wav` from anywhere
else carries the frames alone and arrives at full level with no loop, which is how a player sounds it.

Eight- and sixteen-bit whole amplitudes are what this container reads here, in mono or stereo. A file
stating anything else is refused by name.

The pitch travels as the rate the frames go by, which is what every reader of a `.wav` sounds them at. One
format arrives at its rate through a semitone offset and a finetune trim of its own; those two stay with
the module holding them, and the audio file names the rate they reach.

## Emptying a whole collection

```python
from pathlib import Path

from trackmod import load_voices, save_sample

sounds = Path("sounds")
for path in Path("modules").iterdir():
    for index, sample in enumerate(load_voices(path).samples):
        save_sample(sample, sounds / f"{path.stem}-{index:02d}.wav")
```

`load_voices` reads a module or a standalone instrument file alike, so the same loop empties a directory
holding both. See [`instruments.md`](instruments.md) for the other half: writing each instrument out as a
file a tracker opens.

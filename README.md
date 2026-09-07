# TrackMod

A tracker module is a whole piece of music in one file: the notes, the effects and the recorded sounds all
travel together. TrackMod opens those files, hands you what is inside them, and writes them back out.

| Tracker | Module | One instrument on its own |
|---|---|---|
| Impulse Tracker | `.it` | `.iti` |
| FastTracker 2 | `.xm` | `.xi` |
| Amiga ProTracker | `.mod` | — |
| Scream Tracker 3 | `.s3m` | — |
| Soundtracker | `.mod` | — |

Underneath the five formats there is one model of a song, and each format binds to it. That is what lets
you open a file written by one tracker and save it for another, and what lets you ask — before writing
anything — whether the music fits inside the format you are aiming at.

Sounding the music is a player's job. TrackMod hands you the notes, the settings and the waveforms.

## What you can do with it

- **Open a module** and reach the song inside it: the patterns, the order they play in, the instruments
  and the recorded waveforms.
- **Write a song out** in whichever format you name, learning first how large the file will be and which
  values, if any, that format has no room for.
- **Move a song between formats**, carrying whatever both ends hold.
- **Take the sounds out**: each instrument as an `.iti` or `.xi` file a tracker opens, and each waveform as
  an ordinary `.wav` carrying its loop points, its tuning and its level.

## What it needs

Python 3.12 or newer, `numpy` and `pydantic`.

## Installing it

Add TrackMod as a git submodule, which pins the exact revision you build against:

```bash
git submodule add git@github.com:JakimPL/TrackMod.git TrackMod
git submodule update --init
```

Then point your project at the checkout:

```toml
[project]
dependencies = ["trackmod"]

[tool.uv.sources]
trackmod = { path = "TrackMod", editable = true }
```

## Writing a song to a file

Binding a song to a format gives you a module: something that knows how large the file will be, which of
the song's values that format has room for, and how to write the bytes.

```python
from pathlib import Path

from trackmod import Compliance, ITModule

module = ITModule.from_song(song, compliance=Compliance.CANONICAL)
print(module.size().total)          # the file length, counted from the tables
print(module.violations())          # every bound the song breaks, empty when it is writable
module.save(Path("song.it"))
```

Name another class to write the same song in another format:

```python
from trackmod import XMModule

XMModule.from_song(song, compliance=Compliance.EXTENDED).save(Path("song.xm"))
```

## Taking the sounds out of a collection

```python
from pathlib import Path

from trackmod import Compliance, ITInstrumentFile, load_module, save_sample, units

sounds = Path("sounds")
for path in Path("modules").iterdir():
    module = load_module(path)
    for index, unit in enumerate(units(module.song.voices)):
        instrument = ITInstrumentFile.from_unit(unit, compliance=Compliance.CANONICAL)
        instrument.save(sounds / f"{path.stem}-{index:02d}.iti")

    for index, sample in enumerate(module.song.voices.samples):
        save_sample(sample, sounds / f"{path.stem}-{index:02d}.wav")
```

`load_module` reads the format out of the bytes, so a file that arrived under the wrong name still opens.
`units` hands you each instrument together with the waveforms its keys reach, whichever way the song
addresses them — so the same loop runs over a `.mod`, whose cells name samples, and over an `.it`, whose
cells name instruments.

The `.wav` files carry the loop points, the tuning, the level, the position and the auto-vibrato in the
chunks OpenMPT writes, so a waveform exported here opens in a tracker as the sample it came from, and in
any audio editor as an ordinary sound file.

## Where to read next

See [`docs/`](docs/) for the rest: a guide to each task, a reference for the model and its limits, and
one document per format describing its bytes. Start at [`docs/README.md`](docs/README.md).

## Development

```
make format     # isort + black
make lint       # mypy --strict + pylint
make test       # pytest
make coverage   # pytest with a coverage report
```

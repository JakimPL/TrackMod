# TrackMod

A tracker module is a complete piece of music in one file. It holds the notes, the effects and the recorded
sounds together. TrackMod reads these files, gives you what is inside, and writes them back.

TrackMod supports five formats:

| Tracker | Module | Single instrument |
|---|---|---|
| Impulse Tracker | `.it` | `.iti` |
| FastTracker 2 | `.xm` | `.xi` |
| Amiga ProTracker | `.mod` | — |
| Scream Tracker 3 | `.s3m` | — |
| Soundtracker | `.mod` | — |

All five formats share one model of a song. This lets you:

* open a file written by one tracker and save it for another,
* check whether a song fits a format before you write it.

TrackMod does not play audio. It gives you the notes, the settings and the waveforms. Use a player to hear
them.

## What you can do with it

* Read a module and get the song inside: its patterns, their order, the instruments and the waveforms.
* Write a song in any of the five formats.
* Check the file size and find values the format cannot store, before you write.
* Convert a song from one format to another.
* Save an instrument as an `.iti` or `.xi` file.
* Save a waveform as a `.wav` file.

## Requirements

* Python 3.12 or newer
* `numpy`
* `pydantic`

## Installing

Add TrackMod as a git submodule. This pins the exact version you build against.

```bash
git submodule add git@github.com:JakimPL/TrackMod.git TrackMod
git submodule update --init
```

Then point your project at it:

```toml
[project]
dependencies = ["trackmod"]

[tool.uv.sources]
trackmod = { path = "TrackMod", editable = true }
```

## Reading a file

```python
from pathlib import Path

from trackmod import load_module

module = load_module(Path("song.it"))
print(module.song.name)
print(module.song.patterns[0].cell(row=0, channel=3))
```

TrackMod reads the format from the file contents, not from its name. A file with a wrong or missing
extension still opens.

## Writing a song

Pass a song to a format class. You get a module, which can:

* tell you how large the file will be,
* list the values the format cannot store,
* write the file.

```python
from pathlib import Path

from trackmod import Compliance, ITModule

module = ITModule.from_song(song, compliance=Compliance.CANONICAL)
print(module.size().total)     # how many bytes the file will take
print(module.violations())     # values the format cannot store, empty when the song is writable
module.save(Path("song.it"))
```

`Compliance` sets how strict the check is. See [`docs/reference/limits.md`](docs/reference/limits.md).

To write the same song in another format, use another class:

```python
from trackmod import XMModule

XMModule.from_song(song, compliance=Compliance.EXTENDED).save(Path("song.xm"))
```

## Saving instruments and waveforms

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

`units` gives you every instrument with the waveforms it plays. It works the same for all five formats.

Each `.wav` file keeps the loop points, the tuning, the volume, the panning and the auto-vibrato. You can
open these files in a tracker or in any audio editor.

## Documentation

See [`docs/`](docs/):

* [`docs/guide/`](docs/guide/) — how to do each task,
* [`docs/reference/`](docs/reference/) — the song model and the format limits,
* [`docs/formats/`](docs/formats/) — the byte layout of each format.

Start at [`docs/README.md`](docs/README.md).

## Development

```
make format     # isort + black
make lint       # mypy --strict + pylint
make test       # pytest
make coverage   # pytest with a coverage report
```

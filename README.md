# TrackMod

[![PyPI](https://img.shields.io/pypi/v/trackmod.svg)](https://pypi.org/project/trackmod/)
[![Python](https://img.shields.io/pypi/pyversions/trackmod.svg)](https://pypi.org/project/trackmod/)
[![License](https://img.shields.io/github/license/JakimPL/TrackMod.svg)](https://github.com/JakimPL/TrackMod/blob/main/LICENSE)
[![CI](https://github.com/JakimPL/TrackMod/actions/workflows/ci.yml/badge.svg)](https://github.com/JakimPL/TrackMod/actions/workflows/ci.yml)

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

## Installing

TrackMod needs Python 3.12 or newer. Install it from PyPI:

```bash
pip install trackmod
```

or add it to a [uv](https://docs.astral.sh/uv/) project:

```bash
uv add trackmod
```

This also installs the two libraries TrackMod uses, `numpy` and `pydantic`.

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

`Compliance` sets how strict the check is. See [`docs/reference/limits.md`](https://github.com/JakimPL/TrackMod/blob/main/docs/reference/limits.md).

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

See [`docs/`](https://github.com/JakimPL/TrackMod/tree/main/docs):

* [`docs/guide/`](https://github.com/JakimPL/TrackMod/tree/main/docs/guide) — how to do each task,
* [`docs/reference/`](https://github.com/JakimPL/TrackMod/tree/main/docs/reference) — the song model and the format limits,
* [`docs/formats/`](https://github.com/JakimPL/TrackMod/tree/main/docs/formats) — the byte layout of each format.

Start at [`docs/README.md`](https://github.com/JakimPL/TrackMod/blob/main/docs/README.md). What changed in each release is in
[`CHANGELOG.md`](https://github.com/JakimPL/TrackMod/blob/main/CHANGELOG.md).

## Development

[`docs/contributing/development.md`](https://github.com/JakimPL/TrackMod/blob/main/docs/contributing/development.md) covers the tools, the tests
and the checks a change passes, and [`docs/contributing/releasing.md`](https://github.com/JakimPL/TrackMod/blob/main/docs/contributing/releasing.md)
covers how a release reaches PyPI.

## License

TrackMod is released under the [MIT License](https://github.com/JakimPL/TrackMod/blob/main/LICENSE).

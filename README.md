# TrackMod

A library for reading and writing **tracker modules** — the files a tracker saves a piece of music as, in
which the notes, the effects and the recorded sounds all travel in one file. TrackMod holds a single model
of a song and binds it to each format, so a piece read from one can be written to another.

| Tracker | Module | One instrument on its own |
|---|---|---|
| Impulse Tracker | `.it` | `.iti` |
| FastTracker 2 | `.xm` | `.xi` |
| Amiga ProTracker | `.mod` | — |
| Scream Tracker 3 | `.s3m` | — |

Each format is also described in data: what it can hold, and how much room its fields leave beyond what
the tracker it was written for ever read. A caller can therefore ask what will fit before writing it.

TrackMod depends on `numpy` and `pydantic`, and nothing else. Playing the music and ripping the sounds out
of it are somebody else's job: this library produces and consumes bytes.

```python
from pathlib import Path

from trackmod.trackers.it.module import ITModule
from trackmod.limits.compliance import Compliance

module = ITModule.from_song(song, compliance=Compliance.CANONICAL)
print(module.size().total)          # the file length, without serialising it
print(module.violations())          # every bound the song breaks, empty when it is writable
module.save(Path("song.it"))
```

The same song goes to another format by naming that format's class, and a module read back with
`ITModule.load` yields the same song a writer consumes — so a file in one format can be written to
another, carrying whatever both ends hold.

## Installing it

TrackMod is not published; consumers take it as a git submodule, so a checkout pins the exact revision it
was built against.

```bash
git submodule add git@github.com:JakimPL/TrackMod.git TrackMod
git submodule update --init
```

```toml
[project]
dependencies = ["trackmod"]

[tool.uv.sources]
trackmod = { path = "TrackMod", editable = true }
```

## Documentation

[`docs/overview.md`](docs/overview.md) is the entry point and indexes the rest: the shared model of a song,
the limits system, the pattern columns, and one document per format.

## Development

```
make format     # isort + black
make lint       # mypy --strict + pylint
make test       # pytest
make coverage   # pytest with a coverage report
```

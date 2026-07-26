# TrackMod

A library for reading and writing tracker modules. It holds one format-agnostic domain model of a piece
of tracker music, binds that model to the **Impulse Tracker** (`.it`) and **FastTracker 2** (`.xm`) file
formats, and states in data what each format can carry — including the room a format's fields leave beyond
what the tracker it was written for ever read.

It depends on `numpy` and `pydantic`, and nothing else. Rendering and sample ripping are somebody else's
job: `trackmod` produces and consumes bytes.

```python
from pathlib import Path

from trackmod.it.module import ITModule
from trackmod.limits.compliance import Compliance

module = ITModule.from_song(song, compliance=Compliance.CANONICAL)
print(module.size().total)          # the file length, without serialising it
print(module.violations())          # every bound the song breaks, empty when it is writable
module.save(Path("song.it"))
```

The same song goes to the other format by naming the other class, and a module read back with
`ITModule.load` yields the same `Song` model a writer consumes — so a file in one format can be written to
the other, carrying whatever both formats hold.

## Documentation

[`docs/overview.md`](docs/overview.md) is the entry point and indexes the rest: the shared domain model,
the limits system, the effect column, and one document per format.

## Using it

`trackmod` is not published; consumers take it as a git submodule, so a checkout pins the exact revision it
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

## Development

```
make format     # isort + black
make lint       # mypy --strict + pylint
make test       # pytest
make coverage   # pytest with a coverage report
```

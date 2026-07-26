# trackmod

A library for reading and writing tracker modules. It holds one format-agnostic domain model of a piece
of tracker music, binds that model to the **Impulse Tracker** (`.it`) and **FastTracker 2** (`.xm`) file
formats, and states in data what each format can carry — including the room a format's fields leave
beyond what the tracker it was written for ever read.

It depends on `numpy` and `pydantic`, and nothing else. Rendering and sample ripping are somebody else's
job: `trackmod` produces and consumes bytes.

## Reading order

| Document | What it covers |
|---|---|
| [`model.md`](model.md) | The shared domain model: songs, patterns, samples, instruments, timing |
| [`limits.md`](limits.md) | Capabilities, compliance levels, and where every bound comes from |
| [`effects.md`](effects.md) | The effect column, and the two spellings of one vocabulary |
| [`formats/it.md`](formats/it.md) | What Impulse Tracker stores and how |
| [`formats/xm.md`](formats/xm.md) | What FastTracker 2 stores and how |

## Shape

The library is layered downward: every package depends only on the ones above it.

| Package | Owns |
|---|---|
| `trackmod/spec` | Constants every layer shares: the pitch numbering, level ranges, the grid sentinel, integer widths, the tracker clock |
| `trackmod/schema` | Pydantic plumbing: the frozen model config, the constrained scalar aliases, the numpy array annotations |
| `trackmod/limits` | The capability vocabulary, bounds, compliance levels, violations |
| `trackmod/core` | The format-agnostic music: notes, patterns, samples, instruments, envelopes, songs, timing |
| `trackmod/binary` | Byte-level machinery: declarative records, a cursor, fixed-width text, PCM quantisation and encoding |
| `trackmod/module` | What a format binding offers: the size report, the storage table and the `TrackerModule` protocol |
| `trackmod/trackers/it`, `trackmod/trackers/xm` | One format each: its constants, its record layouts, its packers, parsers, size model and module class |

Each format package repeats the same internal shape, so knowing one is knowing the other:

```
<format>/
  spec/         constants only: identity sizes ranges defaults flags cells effects storage capacities
  layout/       the record layouts, as data: file pattern sample instrument envelope
  effects/      the command enumeration and the catalogue that spells the shared vocabulary
  patterns/     packer, parser, and the size model that is their exact counterpart
  samples/      waveform and header serialisation
  instruments/  header serialisation, keymaps, envelopes
  note limits timing settings checks sizing writer parser module
```

Every `__init__.py` is empty. A name is imported from the module that defines it:

```python
from trackmod.core.songs.song import Song
from trackmod.limits.compliance import Compliance
from trackmod.trackers.it.module import ITModule
from trackmod.trackers.xm.module import XMModule
```

## Writing a module

A `Song` is format-agnostic. Binding it to a format adds that format's own settings and a compliance
level, and produces bytes:

```python
from pathlib import Path

from trackmod.trackers.it.module import ITModule
from trackmod.limits.compliance import Compliance

module = ITModule.from_song(song, compliance=Compliance.CANONICAL)
print(module.size().total)          # the file length, without serialising it
print(module.violations())          # every bound the song breaks, empty when it is writable
module.save(Path("song.it"))
```

The same song goes to the other format by naming the other class:

```python
from trackmod.trackers.xm.module import XMModule

XMModule.from_song(song, compliance=Compliance.EXTENDED).save(Path("song.xm"))
```

## Reading a module

```python
recovered = ITModule.load(Path("song.it"))
recovered.song.patterns[0].cell(row=0, channel=3)
```

Parsing yields the same `Song` model a writer consumes, so a module read from one format can be written
to the other. What survives that trip is what both formats carry — see [`limits.md`](limits.md).

## Budgeting

`module.size()` answers what a song already costs. A caller filling a byte budget asks the question
earlier — how many bytes would one more sample add? — and `module.storage` answers it, as a table of what
each kind of content costs a format:

```python
storage = ITModule.from_song(song, compliance=Compliance.CANONICAL).storage

storage.sample_bytes(frames=22050, depth=BitDepth.SIXTEEN)   # records and frames together
storage.instrument_bytes(samples=4)                          # the header this instrument is written in
storage.frames_budget(48_000, depth=BitDepth.SIXTEEN)        # the longest waveform that still fits
```

Each count covers the table entry a section occupies as well as the record itself, so a format found
through offset tables charges the entry here rather than leaving it for a caller to remember, and
`sample` is charged per stored **slot** — once per waveform where a sample table is shared, once per
owner where an instrument owns its samples.

The table is what each format's size model reads, so `SizeReport.headers` *is* the table evaluated
against the counts a song declares. What the table states and what the writer lays out therefore have one
home, and adding an instrument and its sample grows the file by exactly what
`instrument_bytes` and `sample_bytes` predicted.

## Staying format-agnostic

`ITModule` and `XMModule` share no base class. The surface they have in common is the
`trackmod.module.protocol.TrackerModule` protocol, so a caller that does not care which format it is
holding can say so in its own signature:

```python
from trackmod.module.protocol import TrackerModule

def report(module: TrackerModule) -> str:
    return f"{module.size().total} bytes as {module.extension}"
```

## Conventions

- Every validated or serialised type is a **frozen** Pydantic model. Bounds live in `Field(...)`
  constraints and cross-field rules in `model_validator(mode="after")`.
- Constants live in `spec/` packages and nowhere else, so the constants read as the specification.
- Protocols are preferred to base classes, and composition to inheritance.
- The library carries no module docstrings and no code comments. Class and function docstrings state
  intent; the domain and format narrative lives in these documents.

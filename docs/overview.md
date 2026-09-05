# Overview

This is the entry point to the documentation. TrackMod reads and writes tracker modules through one
format-agnostic model of a piece of music, and the documents below take that apart from three directions:
what the model holds, what each format can carry, and how the two are joined.

## Reading order

| Document | What it covers |
|---|---|
| [`model.md`](model.md) | The shared model: songs, patterns, voices, samples, instruments, timing |
| [`limits.md`](limits.md) | Capabilities, compliance levels, and where every bound comes from |
| [`effects.md`](effects.md) | The effect column, and the one vocabulary each format spells its own way |
| [`volume.md`](volume.md) | The volume column: one vocabulary, and what each format's byte reaches |
| [`formats/README.md`](formats/README.md) | The formats side by side, and where they disagree about one field |
| [`formats/it.md`](formats/it.md) | What Impulse Tracker stores, and how |
| [`formats/xm.md`](formats/xm.md) | What FastTracker 2 stores, and how |
| [`formats/mod.md`](formats/mod.md) | What Amiga ProTracker stores, and how |
| [`formats/s3m.md`](formats/s3m.md) | What Scream Tracker 3 stores, and how |
| [`conventions.md`](conventions.md) | How these documents and this library are written |

## Shape

The library is layered downward: every package depends only on the ones above it.

| Package | Owns |
|---|---|
| `trackmod/spec` | Constants every layer shares: the pitch numbering, level ranges, the grid sentinel, integer widths, the tracker clock |
| `trackmod/schema` | Pydantic plumbing: the frozen model config, the constrained scalar aliases, the numpy array annotations |
| `trackmod/limits` | The capability vocabulary, bounds, compliance levels, violations |
| `trackmod/core` | The format-agnostic music: notes, patterns, samples, instruments, envelopes, voices, songs, timing |
| `trackmod/binary` | Byte-level machinery: declarative records, a cursor, fixed-width text, PCM quantisation and encoding |
| `trackmod/module` | What a format binding offers: the size report, the storage table and the `TrackerModule` and `InstrumentFile` protocols |
| `trackmod/trackers/<format>` | One format each: its constants, its record layouts, its packers, parsers, size model, module class and instrument-file class |

Each format package repeats the same internal shape, so knowing one is knowing the next:

```
<format>/
  spec/         constants only: identity sizes ranges defaults flags cells effects storage capacities
  layout/       the record layouts, as data: file pattern sample instrument envelope
  effects/      the command enumeration and the catalogue that spells the shared vocabulary
  patterns/     packer, parser, and the size model that is their exact counterpart
  samples/      waveform and header serialisation
  instruments/  header serialisation, keymaps, envelopes, the standalone instrument file
  note limits timing fade settings checks sizing writer parser module instrument_file
```

A package holds the parts its own format keeps records for: the three whose cells name a sample directly
have no `instruments/` and no envelopes, and each format adds the files its layout calls for — a table of
dialects for Amiga ProTracker, the paragraph arithmetic for Scream Tracker 3.

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

The same song goes to another format by naming that format's class:

```python
from trackmod.trackers.xm.module import XMModule

XMModule.from_song(song, compliance=Compliance.EXTENDED).save(Path("song.xm"))
```

A format states which kind of voice table it writes — samples a cell names directly, or instruments that
route keys onto samples — so a song carrying the other kind is refused by name, and
`trackmod.core.voices.convert` is where a caller turns one into the other deliberately. See
[`model.md`](model.md).

## Reading a module

```python
recovered = ITModule.load(Path("song.it"))
recovered.song.patterns[0].cell(row=0, channel=3)
```

Parsing yields the same `Song` model a writer consumes, so a module read from one format can be written to
another. What survives that trip is what both ends carry — see [`limits.md`](limits.md). A file stating
a value the model holds no room for is read as it stands and reported, once, as a `RepairWarning`.

A module also says how far it reaches past the tracker its format names: `recovered.reach` is the strictest
of the three levels its values fit inside, and `recovered.exceeded()` is which ceilings it passed to get
there.

## One instrument on its own

The two formats that keep instrument records also store a single voice as a file of its own — `.iti` and
`.xi` — which is what a producer of sampled instruments ships when the instrument is the product. The
content is an `InstrumentUnit`: one instrument and the samples its keymap reaches (see
[`model.md`](model.md)).

```python
from trackmod.trackers.it.instrument_file import ITInstrumentFile

instrument = ITInstrumentFile.load(Path("piano.iti"))
print(instrument.unit.instrument.name, len(instrument.unit.samples))
print(instrument.size().total)      # the file length, without serialising it
print(instrument.violations())      # every bound the unit breaks, empty when it is writable
```

The surface mirrors a module's, so the two are read the same way. `trackmod.module.instrument.InstrumentFile`
is the protocol a caller names to hold one of either format:

```python
from trackmod.module.instrument import InstrumentFile

def report(instrument: InstrumentFile) -> str:
    return f"{instrument.size().total} bytes as {instrument.extension}"
```

## Reading whichever container a producer ships

A producer of sampled instruments picks the container: a whole module, or one voice on its own, in either
format. A consumer holding the bytes and the extension they were written under reads them all the same
way, through `trackmod.trackers.registry`:

```python
from trackmod.trackers.registry import EXTENSIONS, parse_voices

voices = parse_voices(path.read_bytes(), extension=path.suffix)
```

The result is the voice table the format that wrote the bytes addresses, so the choice of container stops
mattering at the point the bytes are read. The extension is matched in either capitalisation, and one that
no format here writes is refused by name. `EXTENSIONS`, `MODULE_EXTENSIONS` and `INSTRUMENT_EXTENSIONS`
state which suffixes are read, so the suffix table lives here, once.

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
through offset tables charges the entry here, where a caller budgets against one number, and `sample`
is charged per stored **slot** — once per waveform where a sample table is shared, once per owner where an
instrument owns its samples.

The table is what each format's size model reads, so `SizeReport.headers` *is* the table evaluated against
the counts a song declares. What the table states and what the writer lays out therefore have one home,
and adding an instrument and its sample grows the file by exactly what `instrument_bytes` and
`sample_bytes` predicted.

## Staying format-agnostic

The module classes share no base class, and neither do the instrument-file classes. The surface each pair
has in common is a protocol — `trackmod.module.protocol.TrackerModule` and
`trackmod.module.instrument.InstrumentFile` — so a caller holding either of them can say so in its own
signature:

```python
from trackmod.module.protocol import TrackerModule

def report(module: TrackerModule) -> str:
    return f"{module.size().total} bytes as {module.extension}"
```

## Conventions

How these documents and this library are written is stated once, in [`conventions.md`](conventions.md).

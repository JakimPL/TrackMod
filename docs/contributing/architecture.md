# Architecture

The decisions the library's own shape rests on: how the packages are layered, what each one owns, and
which of them may read which.

## Layers

The library is layered downward: every package reads its own layer and the ones above it in this table.

| Package | Owns |
|---|---|
| `trackmod/spec` | Constants every layer shares: the pitch numbering, level ranges, the volume-column grid, the grid sentinel, integer widths, the tracker clock, the tracker character set, this library's own name and version |
| `trackmod/utils` | Arithmetic the timing lattice leans on: the divisors of a number, and the two of them nearest a candidate |
| `trackmod/schema` | Pydantic plumbing: the frozen model config, the constrained scalar aliases, the numpy array annotations |
| `trackmod/limits` | The capability vocabulary, bounds, compliance levels, violations |
| `trackmod/core` | The format-agnostic music: notes, patterns, samples, instruments, envelopes, voices, songs, timing |
| `trackmod/binary` | Byte-level machinery: declarative records, a cursor, fixed-width text, PCM quantisation and encoding |
| `trackmod/wave` | The RIFF audio container: its chunk layouts, and a sample written and read as a `.wav` |
| `trackmod/module` | What a format binding offers: the size report, the storage table, how far a file's values reach, and the `TrackerModule` and `InstrumentFile` protocols |
| `trackmod/trackers/<lineage>` | What a family of formats inherited from the one that settled it: the Amiga period tables, the fixed cell, the thirty-byte sample record |
| `trackmod/trackers/<format>` | One format each: its constants, its record layouts, its packers, parsers, size model, module class and instrument-file class |

`tests/test_boundaries.py` reads the import graph and holds this order, so knowing where a name lives is
knowing what may reach it.

## The package root

`trackmod/__init__.py` carries what a caller needs to **open a file, reach the music inside it, and write
it back out**. Everything else is imported from the module that defines it.

```python
from trackmod import Compliance, ITModule, load_module, save_sample, units
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.trackers.s3m.settings import S3MSettings
```

Patterns, cells, envelopes, timing, the settings models, the effect catalogues, the storage and size
reports and everything under `binary` keep their module paths. They belong to callers building songs
rather than reading them, and the root stays a surface a newcomer can read in one screen. The root stands
above every layer and reads all of them; every other `__init__.py` is empty.

## A format package

Each format package repeats the same internal shape, so knowing one is knowing the next:

```
<format>/
  spec/         constants only: identity sizes ranges defaults flags cells effects storage capacities
  layout/       the record layouts, as data: file pattern sample instrument envelope
  effects/      the command enumeration and the catalogue that spells the shared vocabulary
  patterns/     packer, parser, and the size model that is their exact counterpart
  samples/      waveform and header serialisation
  instruments/  header serialisation, keymaps, envelopes, the standalone instrument file
  detection limits timing settings sizing writer parser module
```

The last line is what every format has: what its bytes state about themselves, its capacities read at one
level, its clock, its own settings, its size model, and the pair that writes and reads a whole file behind
the module class.

A package holds the subdirectories its own format keeps records for. The three that keep no instrument
records — Amiga ProTracker, Scream Tracker 3 and Soundtracker — have no `instruments/` and no envelopes,
and the two Amiga layouts read their `patterns/` and `samples/` from the lineage that holds both.

Each format then adds the files its layout calls for: `note`, `fade`, `checks` and `instrument_file` where
a format keeps instrument records, `dialect` and `tag` for the four characters that name an Amiga layout,
`parapointers` and `placement` for the paragraphs Scream Tracker 3's blocks open on, `tuning` where a
header states a transposition rather than a rate, and `version` where a file numbers its writer.

## Lineage packages

A lineage package sits beside the formats in the same shape and holds what a family of them shares.
`amiga/` is the one this library has: the period tables, the four-byte cell, the thirty-byte sample record
and the eight-bit waveform that Ultimate Soundtracker settled and every tracker on that machine kept,
together with the walk that reads a file of either and the checks that grade a song for both. Its own
files carry the same names — `reading`, `writing`, `sizing`, `checks`, `note`, `tuning` beside `spec/`,
`layout/`, `patterns/` and `samples/` — so the shape above reads the same there.

A format package owns every decision its own file layout makes, and every import it makes reaches its
lineage or a layer beneath it. Two formats sharing a decision because one inherited it from the other
share it through the lineage, which owns it outright; where they disagree, the lineage takes the answer as
an argument, so each of them keeps its own. `tests/test_boundaries.py` holds that line.

## Validating versus repairing

> **A validator constrains what the library writes. A parser repairs what it reads, and says so.**

| Situation | Mechanism | Where it is documented |
|---|---|---|
| A quantity past what a format holds | `Violation`, collected into one `LimitError` | [`../reference/limits.md`](../reference/limits.md), and the format's capacities |
| Content with no encoding at all | `ValueError` where it is met | the format document's refusals table |
| A value a real file states that the model holds no room for | drawn into range, gathered in `Repairs`, reported once as a `RepairWarning` | the format document, under the section that reads it |

A bound says *use a smaller number*. A `ValueError` says *this idea has no home here, express it another
way*. A repair says *the file stated something odd, and this is what was heard*.

## Types

- Every validated or serialised type is a **frozen** Pydantic model. Bounds live in `Field(...)`
  constraints, and cross-field rules in `model_validator(mode="after")`.
- Constants live in `spec/` packages and nowhere else, so the constants read as the specification.
- Protocols are preferred to base classes, and composition to inheritance. `Reaching` is the one mixin,
  carrying no fields, no construction and no format knowledge, which is what earns it the exception.

# Conventions

The rules these documents are written to. They exist so a reader can predict what a document will tell
them, and so that adding a fifth format touches one new file and one column in five tables.

## Three tiers

| Tier | Documents | Register |
|---|---|---|
| Guide | [`../README.md`](../README.md), [`overview.md`](overview.md) | Plain English. Type names where a caller types them, and no byte offsets. |
| Reference | [`model.md`](model.md), [`limits.md`](limits.md), [`effects.md`](effects.md), [`volume.md`](volume.md) | Plain English about a technical subject. Type names are the payload. |
| Specification | [`formats/`](formats/) | Offsets, widths, bit meanings. Dense through tables. |

Where a document sits declares its tier. A reader opening a format document expects byte offsets; a
reader opening the README expects a sentence about what the library is for.

## How much detail

> **Locate and interpret. Leave reproducing to the code.**

A format document states everything needed to **locate** a value — record, offset, width, byte order —
and to **interpret** it: what the values mean, what each bit switches.

A formula belongs in a document where the format defines it, as the frequency table, the tick clock and
the fade counter do. A formula that is one of several correct ways to compute the same answer belongs in
a docstring, beside the code that picked one.

## Positive voice

State what a record, a class or a function **does**. Every negation is reframed into the behaviour that
actually happens: "there is no shared sample table" is written "each instrument carries its own copies of
the samples its keys reach".

Three rules follow from it:

1. **Absence is a table cell.** A format missing a field gets a `—` in the fixed tables below.
2. **Prose names what the record carries**, at the point a reader would look for the missing thing.
3. **Refusals are a contract**, so they may be negative — and they live in exactly one table per
   document, headed `Content | Reported as`.

Negation is otherwise reserved for exception triggers, precondition bounds, and documented edge-case
returns, where the condition itself is the contract.

## Code references

| Tier | Budget |
|---|---|
| Guide | 4 in prose; `overview.md`'s package table and format tree are the map, and are exempt |
| Reference | 8 per document |
| Specification | none |

A reference is a **dotted importable path** to a name a caller types, so `trackmod.core.songs.song.Song`
rather than a file path. A format document names records and fields instead: its subject is the file, and
a reader who wants the code has `overview.md`'s tree.

## Validating versus repairing

> **A validator constrains what the library writes. A parser repairs what it reads, and says so.**

| Situation | Mechanism | Where it is documented |
|---|---|---|
| A quantity past what a format holds | `Violation`, collected into one `LimitError` | [`limits.md`](limits.md), and the format's capacities |
| Content with no encoding at all | `ValueError` where it is met | the format document's refusals table |
| A value a real file states that the model holds no room for | drawn into range, gathered in `Repairs`, reported once as a `RepairWarning` | the format document, under the section that reads it |

A bound says *use a smaller number*. A `ValueError` says *this idea has no home here, express it another
way*. A repair says *the file stated something odd, and this is what was heard*.

## The format-document template

Every document under `formats/` uses these headings in this order. A section covering something only some
formats hold keeps its row in the fixed tables and drops its heading.

```
# <Tracker> (`.<ext>`)
   orientation — the tracker, the year, what a file holds. No offsets yet.
## At a glance                   the fixed table below
## File shape                    where the sections sit, as a diagram
## Order list
## Patterns
### The note column
### The instrument column
### The volume column
## Instruments
### Envelopes
### Fadeout
## Samples
### Tuning
## Later additions               what writers after the original tracker appended
## One instrument on its own
## Timing
## What this format carries      the fixed table below, then the refusals table
## Effect commands
```

**Budget: 115 lines of prose, and a prose paragraph runs to five lines at most.** A whole document
lands near 280 lines, of which the two fixed tables are about 50: density belongs in the tables, and the
prose budget is what keeps a document readable.

### The two fixed tables

`At a glance` and `What this format carries` carry the **same rows in the same order** in every format
document. That is what makes the four diffable, and what lets an absence be a `—` rather than a sentence.

`At a glance` orients, in these rows:

```
Tracker · Byte order · A cell's instrument column names · Sections are found by ·
Channels · Pattern rows · Note range · Waveform storage · One instrument on its own
```

`What this format carries` states presence, with the bound or the shape where a format has the field
and `—` where it has none, in these rows:

```
Shared sample table · Volume envelope · Panning envelope · Pitch envelope · Envelope sustain ·
Envelope carry · Fadeout · New note action · Sample volume · Sample gain · Sample panning ·
Sample auto-vibrato · Sample loop · Sustain loop · Stereo waveforms · Compressed waveforms ·
Note column commands · Song message · Song volume · Mix volume · Channel panning table
```

A refusals table follows it under the same heading, listing what a format has no encoding for at all.

## Library conventions

- Every validated or serialised type is a **frozen** Pydantic model. Bounds live in `Field(...)`
  constraints, and cross-field rules in `model_validator(mode="after")`.
- Constants live in `spec/` packages and nowhere else, so the constants read as the specification.
- Protocols are preferred to base classes, and composition to inheritance.
- The library carries no module docstrings and no code comments. Class and function docstrings state
  intent; the domain and format narrative lives in these documents.

# Reading a module

Open a file and you get a module: the song inside it, what the file said about itself, and how far its
values reach past the tracker its format names.

```python
from pathlib import Path

from trackmod import load_module

module = load_module(Path("song.it"))
module.song.patterns[0].cell(row=0, channel=3)
```

`load_module` reads the format out of the bytes, so a file that was renamed, repacked or shared under a
habit rather than a rule still opens as what it is. Every format but one opens a file with a tag or a name
of its own, and the one that opens with neither is recognised by its records adding up to the length of
the file.

Naming a format yourself is the other way in, and it takes the bytes directly:

```python
from trackmod import ITModule, parse_module

module = ITModule.load(Path("song.it"))
module = parse_module(data, extension=".it")
```

Parsing yields the same `Song` a writer consumes, so a module read from one format can be written to
another. What survives that trip is what both ends carry — see [`../reference/limits.md`](../reference/limits.md).

## What the file stated about itself

`module.provenance` names the program that wrote the bytes, where the file states one, and says which kind
of statement carried it: a name the header spells outright, a mark a writer signed into bytes the format
reserves, a program number above a version, or the tag naming the family that settled the layout. It is
`None` for the one format whose files name their writer nowhere.

`module.reach` is the strictest of the three compliance levels the file's values fit inside — or `None`
for a song carrying a value no record layout holds — and `module.exceeded()` is which ceilings it passed
to get there. See [`../reference/limits.md`](../reference/limits.md).

## When a file states something odd

A file written by a real tracker states values the model holds no room for: an envelope loop ending before
it begins, a sample loop reaching past the waveform, an order naming a pattern the file leaves out. The
parser draws each of those into range and gathers what it did, reporting everything as one `RepairWarning`:

```
RepairWarning: values drawn into range as the file was read: sample 3: rate 0 read as 8363 Hz;
song: 2 order positions naming no stored pattern dropped
```

Which values a given format repairs is stated in its own document, under the section that reads them.

## Two formats share one suffix

`.mod` names two layouts, because the older of them was written before a name carried an extension at all,
so that suffix is read from the bytes rather than the name: a file carrying a tag states which tracker
wrote it and is read as Amiga ProTracker, and a file whose own records add up to its length behind a
600-byte header is read as Soundtracker. This is the one place that knows both, which is what keeps either
format free of the other.

`detected` answers the same question on its own, for a caller holding bytes rather than a path:

```python
from trackmod import detected, parse_module

data = path.read_bytes()
module = parse_module(data, extension=detected(data))
```

Each format states its own answer, so the tag offsets stay with the format that chose them, and the
strongest statement is asked first. Bytes stating none of the formats are refused by name.

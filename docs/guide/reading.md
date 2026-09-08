# Reading a module

`load_module` opens a file and gives you a module. A module holds three things:

* `song` — the music: the patterns, their order, the instruments and the waveforms,
* `provenance` — what the file says about the program that wrote it,
* `reach` — how far its values go past what its own tracker allowed.

```python
from pathlib import Path

from trackmod import load_module

module = load_module(Path("song.it"))
module.song.patterns[0].cell(row=0, channel=3)
```

TrackMod reads the format from the file contents, not from its name, so a file that was renamed or saved
with the wrong extension still opens. Four of the five formats begin with a tag or a name of their own. The
fifth has neither, and TrackMod recognizes it because its records add up to the length of the file.

If you already know the format, name it yourself and pass the bytes directly:

```python
from trackmod import ITModule, parse_module

module = ITModule.load(Path("song.it"))
module = parse_module(data, extension=".it")
```

Reading gives you the same `Song` that writing takes, so you can read a file in one format and write it in
another. What survives the trip is what both formats support. See
[`../reference/limits.md`](../reference/limits.md).

## What the file says about itself

`module.provenance` names the program that wrote the file, when the file says so. It also says how the file
stated it:

* a name written into the header,
* a mark the writer signed into bytes the format reserves,
* a program number above a version,
* the tag naming the format family.

It is `None` for the one format whose files never name their writer.

`module.reach` is the strictest compliance level the file's values fit inside. It is `None` when the song
carries a value no format layout can hold. `module.exceeded()` lists the limits the file passed to get
there. See [`../reference/limits.md`](../reference/limits.md).

## When a file holds something odd

Real trackers write values the model has no room for:

* an envelope loop that ends before it begins,
* a sample loop that reaches past the waveform,
* an order position naming a pattern the file does not store.

TrackMod pulls each value back into range, collects what it changed, and reports it all as one
`RepairWarning`:

```
RepairWarning: values drawn into range as the file was read: sample 3: rate 0 read as 8363 Hz;
song: 2 order positions naming no stored pattern dropped
```

Each format document lists the values that format repairs.

## Two formats share the `.mod` extension

`.mod` names two layouts. The older one was written before file names carried extensions at all, so TrackMod
tells the two apart by their contents:

* a file with a tag says which tracker wrote it, and is read as Amiga ProTracker,
* a file whose records add up to its length behind a 600-byte header is read as Soundtracker.

`detected` answers the same question on its own, for when you hold bytes rather than a path:

```python
from trackmod import detected, parse_module

data = path.read_bytes()
module = parse_module(data, extension=detected(data))
```

Each format checks its own bytes, and the strongest signal wins. Bytes matching no format raise a
`ValueError`.

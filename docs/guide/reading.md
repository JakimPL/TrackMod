# Reading a module

`load_module` opens a file and returns a module. A module holds three things:

* `song`: the music, meaning the patterns, their order, the instruments and the waveforms.
* `provenance`: what the file says about the program that wrote it.
* `reach`: how far the file's values go beyond what its own tracker allowed.

```python
from pathlib import Path

from trackmod import load_module

module = load_module(Path("song.it"))
module.song.patterns[0].cell(row=0, channel=3)
```

TrackMod detects the format from the file contents, so a file with a wrong or missing extension still
opens. Four of the five formats start with a tag or a name that identifies them. The fifth, Soundtracker,
has neither, so TrackMod checks whether its records add up to the length of the file.

If you already know the format, name it. `ITModule.load` reads a file, and `parse_module` reads bytes:

```python
from pathlib import Path

from trackmod import ITModule, parse_module

module = ITModule.load(Path("song.it"))
module = parse_module(Path("song.it").read_bytes(), extension=".it")
```

The `Song` you read is the same kind of object you write, so you can read a file in one format and save it
in another. What survives is what both formats can store. See
[`../reference/limits.md`](../reference/limits.md).

## What the file says about itself

`module.provenance` names the program that wrote the file, if the file says so. It also tells you how the
file said it:

* a name written in the header,
* a mark the writer left in bytes the format reserves,
* a program number stored in the version field,
* a tag that names the format family.

It is `None` for Soundtracker, whose files never say which program wrote them.

`module.reach` is the strictest compliance level the file's values fit. It is `None` when the song holds a
value that no format can store. `module.exceeded()` lists the limits the file goes past. See
[`../reference/limits.md`](../reference/limits.md).

## When a file holds out-of-range values

Real trackers sometimes write values the model cannot hold:

* an envelope loop that ends before it begins,
* a sample loop that runs past the end of the waveform,
* an order position that points to a missing pattern.

TrackMod moves each of these values back into range, keeps a list of every change, and reports the whole
list as one `RepairWarning`:

```
RepairWarning: values drawn into range as the file was read: sample 3: rate 0 read as 8363 Hz;
song: 2 order positions naming no stored pattern dropped
```

Each [format document](../formats/README.md) lists the values that format repairs.

## Two formats share the `.mod` extension

`.mod` names two layouts. The older one predates file extensions, so TrackMod tells them apart by content:

* A file with a tag names the tracker that wrote it, and TrackMod reads it as Amiga ProTracker.
* A file whose records add up to its length behind a 600-byte header is read as Soundtracker.

`detected` answers the same question by itself, for when you hold bytes instead of a path:

```python
from pathlib import Path

from trackmod import detected, parse_module

data = Path("song.mod").read_bytes()
module = parse_module(data, extension=detected(data))
```

Each format checks its own bytes. Tags are checked first, so a tag settles the answer before the length
check runs. Bytes that match no format raise a `ValueError`.

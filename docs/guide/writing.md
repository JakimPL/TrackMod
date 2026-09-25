# Writing a song to a file

A `Song` is format-neutral. To write one, pass it to a format class. You get a module that adds the
format's settings and a compliance level, and can produce the bytes.

```python
from pathlib import Path

from trackmod import Compliance, ITModule

module = ITModule.from_song(song, compliance=Compliance.CANONICAL)
print(module.size().total)     # how many bytes the file will take
print(module.violations())     # values the format cannot store, empty when the song is writable
module.save(Path("song.it"))
```

`size()` tells you the file size before you write anything. `violations()` lists every limit the song breaks
at the compliance level you chose. `to_bytes()` and `save()` refuse a song that has any violation and raise
one `LimitError` that lists them all. See [`../reference/limits.md`](../reference/limits.md) for the three
levels and how to pick one.

A format can also fail for a second reason: some content has no encoding in the format at all, so there is
no limit to report it against. That raises a `ValueError`. The two errors call for different fixes:

* `LimitError` means *use a smaller number*.
* `ValueError` means *this format cannot store this at all, so express it another way*.

## The settings a format keeps

Each format has its own frozen settings model next to its module class: `ITSettings`, `XMSettings`,
`MODSettings`, `S3MSettings` and `STSettings`. Each lives in the `settings` module of its format package.
Settings hold what is specific to the format, such as the tag an Amiga ProTracker module is written under,
a channel panning table, a mix volume, a song message, or the version the file claims.

A new song starts with the values the format's own tracker wrote, so you only set a setting when you want a
different value:

```python
from trackmod.trackers.s3m.module import S3MModule
from trackmod.trackers.s3m.settings import S3MSettings

S3MModule.from_song(song, compliance=Compliance.CANONICAL, settings=S3MSettings(mix_volume=48))
```

A module read from a file keeps the settings it came with, so saving it again writes them unchanged.

## Which program the file names

One setting names the program that wrote the file. The formats store it in different ways:

* FastTracker 2 is the one format with room for a name: twenty bytes of header text. A song built with
  TrackMod is signed with this library's name and version.
* Impulse Tracker and Scream Tracker 3 store a number instead. Each number belongs to the program that
  claimed it, so a song built here stores the number its own format settled on.

Either field is a setting, so you can set a different value.

## The voice table a format writes

Each format stores one kind of voice table: either samples that a cell names directly, or instruments that
route keys to samples. A song that holds the other kind is refused. Use `raised` and `flattened` to convert
between the two. See [`converting.md`](converting.md) and [`../reference/model.md`](../reference/model.md).

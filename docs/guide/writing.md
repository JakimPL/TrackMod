# Writing a song to a file

A `Song` belongs to no format. Pass it to a format class and you get a module, which adds that format's own
settings and a compliance level, and can produce the bytes.

```python
from pathlib import Path

from trackmod import Compliance, ITModule

module = ITModule.from_song(song, compliance=Compliance.CANONICAL)
print(module.size().total)     # how many bytes the file will take
print(module.violations())     # values the format cannot store, empty when the song is writable
module.save(Path("song.it"))
```

`size()` answers before anything is written. `violations()` lists every limit the song breaks at the level
you chose. `to_bytes()` and `save()` refuse a song with any violation and raise one `LimitError` carrying
all of them. See [`../reference/limits.md`](../reference/limits.md) for the three levels and how to choose
one.

A format can also fail for a second reason. Some content has no encoding in a format at all, so there is no
limit to report it against. That raises a `ValueError` instead. The two errors ask for different fixes:

* `LimitError` means *use a smaller number*,
* `ValueError` means *this format has no way to store this at all; express it differently*.

## The settings a format keeps

Each format keeps its own frozen settings model beside its module class: `ITSettings`, `XMSettings`,
`MODSettings`, `S3MSettings` and `STSettings`, each in its package's `settings` module. These hold what
belongs to the format rather than to the music, such as the tag an Amiga ProTracker module is written under,
a channel panning table, a mix volume, a song message, or the version the file claims.

A new song leaves the settings at what the format's own tracker wrote, so you only name them when you want a
particular value:

```python
from trackmod.trackers.s3m.module import S3MModule
from trackmod.trackers.s3m.settings import S3MSettings

S3MModule.from_song(song, compliance=Compliance.CANONICAL, settings=S3MSettings(mix_volume=48))
```

A module read from a file keeps the settings it arrived with, so writing it again stores them unchanged.

## Which program the file names

One setting names the writer. Only FastTracker 2 gives it room for a name: twenty bytes of header text,
where a song built here is signed with this library's name and version. Impulse Tracker and Scream Tracker 3
store a number there instead, and each number belongs to the program that took it, so a song built here
stores the number its own format settled on. Either field is a setting, so you can state a different one.

## The voice table a format writes

Each format stores one kind of voice table: samples a cell names directly, or instruments that route keys
onto samples. A song holding the other kind is refused by name. Use `raised` and `flattened` to convert
between them. See [`converting.md`](converting.md) and [`../reference/model.md`](../reference/model.md).

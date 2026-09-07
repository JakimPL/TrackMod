# Writing a song to a file

A `Song` belongs to no format. Binding it to one adds that format's own settings and a compliance level,
and produces bytes.

```python
from pathlib import Path

from trackmod import Compliance, ITModule

module = ITModule.from_song(song, compliance=Compliance.CANONICAL)
print(module.size().total)          # the file length, counted from the tables
print(module.violations())          # every bound the song breaks, empty when it is writable
module.save(Path("song.it"))
```

`size()` answers before anything is serialised, and `violations()` lists every bound the song breaks at
the level you chose. `to_bytes()` and `save()` refuse a song with any violation, raising one `LimitError`
carrying all of them. See [`../reference/limits.md`](../reference/limits.md) for what the three levels
mean and how to choose one.

Content a format has no encoding for at all is a different answer: it raises `ValueError` where it is met,
because there is no bound to report it against. A `LimitError` says *use a smaller number*; a `ValueError`
says *this idea has no home in this format, express it another way*.

## The settings a format keeps

Each format keeps a frozen settings model beside its module class — `ITSettings`, `XMSettings`,
`MODSettings`, `S3MSettings` and `STSettings`, each in its package's `settings` module. They hold what
belongs to a format rather than to the music: the tag an Amiga ProTracker module is written under, a
channel panning table, a mix volume, a song message, the version a file claims to have been written by.

A song built from nothing leaves the settings at what its format's own tracker wrote, so naming them is
only for a caller who wants one of them stated:

```python
from trackmod.trackers.s3m.module import S3MModule
from trackmod.trackers.s3m.settings import S3MSettings

S3MModule.from_song(song, compliance=Compliance.CANONICAL, settings=S3MSettings(mix_volume=48))
```

A module read from a file carries the settings it arrived with, so writing it again states them unchanged.

## Which program the file names

One settings value names the writer, and only FastTracker 2 gives it room for a name: twenty bytes of
header text, where a song built here is signed with this library's name and the version of the package
doing the writing. Impulse Tracker and Scream Tracker 3 spend a number there, and each of those numbers
belongs to the program that took it, so a song built here states the one its own format settled — the
revision a reader reads the file under. Either field is a settings value, so a caller states another where
they want one.

## The voice table a format writes

A format states which kind of voice table it writes — samples a cell names directly, or instruments that
route keys onto samples — so a song carrying the other kind is refused by name. `raised` and `flattened`
turn one into the other deliberately; see [`converting.md`](converting.md) and
[`../reference/model.md`](../reference/model.md).

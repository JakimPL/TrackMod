# Moving a song between formats

Reading yields the same `Song` a writer consumes, so a module read in one format is written in another by
naming that format's class:

```python
from pathlib import Path

from trackmod import Compliance, ITModule, XMModule

song = ITModule.load(Path("song.it")).song
XMModule.from_song(song, compliance=Compliance.EXTENDED).save(Path("song.xm"))
```

What survives the trip is what both ends hold. Ask before writing: `violations()` lists every quantity the
target format has no room for, and [`../reference/limits.md`](../reference/limits.md) has the whole table.

## Changing how the song addresses its voices

A cell's instrument column names either a sample or an instrument, and each format states which kind it
writes. A song carrying the other kind is refused by name, and the conversion is a call you make:

```python
from trackmod import flattened, raised

song.model_copy(update={"voices": flattened(song.voices)})   # instruments onto plain samples
song.model_copy(update={"voices": raised(song.voices)})      # samples onto instruments of their own
```

`raised` always succeeds: every sample gains an instrument routing every key to it at its own pitch.
`flattened` refuses an instrument that reaches several samples or sounds a key at another key's pitch,
since a table of samples holds room for neither — so turning a FastTracker 2 song into one a
sample-addressed format can write is a visible step with a visible failure.
See [`../reference/model.md`](../reference/model.md).

## Holding any format at once

The module classes share no base class, and neither do the instrument-file classes. What each pair has in
common is a protocol — `trackmod.module.protocol.TrackerModule` and
`trackmod.module.instrument.InstrumentFile` — so a caller holding either says so in its own signature:

```python
from trackmod import TrackerModule

def report(module: TrackerModule) -> str:
    return f"{module.size().total} bytes as {module.extension}"
```

`load_module` returns one of these, so a loop over a mixed collection holds every format the same way and
reaches the song, the provenance and the size report of each through one surface.

# Converting a song between formats

Reading gives you the same `Song` that writing takes, so you can read a module in one format and write it in
another by naming that format's class:

```python
from pathlib import Path

from trackmod import Compliance, ITModule, XMModule

song = ITModule.load(Path("song.it")).song
XMModule.from_song(song, compliance=Compliance.EXTENDED).save(Path("song.xm"))
```

What survives is what both formats support. Check before you write: `violations()` lists every value the
target format cannot store, and [`../reference/limits.md`](../reference/limits.md) has the full table.

## Changing how the song addresses its voices

A cell's instrument column names either a sample or an instrument, and each format stores one kind only. A
song holding the other kind is refused by name, so the conversion is a call you make:

```python
from trackmod import flattened, raised

song.model_copy(update={"voices": flattened(song.voices)})   # instruments onto plain samples
song.model_copy(update={"voices": raised(song.voices)})      # samples onto instruments of their own
```

`raised` always works: every sample gains an instrument that routes every key to it at that key's own pitch.

`flattened` refuses an instrument that reaches several samples, or that plays a key at another key's pitch,
because a table of samples has no room for either. So converting a FastTracker 2 song into one a
sample-based format can write is a visible step that can visibly fail. See
[`../reference/model.md`](../reference/model.md).

## Holding any format at once

The module classes share no base class, and neither do the instrument-file classes. Each pair shares a
protocol instead: `trackmod.module.protocol.TrackerModule` and `trackmod.module.instrument.InstrumentFile`.
Name the protocol to accept any format:

```python
from trackmod import TrackerModule

def report(module: TrackerModule) -> str:
    return f"{module.size().total} bytes as {module.extension}"
```

`load_module` returns one of these, so a loop over a mixed folder handles every format the same way and
reaches each file's song, provenance and size report through one interface.

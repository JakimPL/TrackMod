# Converting a song between formats

The `Song` you read is the same kind of object you write, so you can read a module in one format and write
it in another. Pass the song to the other format's class:

```python
from pathlib import Path

from trackmod import Compliance, ITModule, XMModule

song = ITModule.load(Path("song.it")).song
XMModule.from_song(song, compliance=Compliance.EXTENDED).save(Path("song.xm"))
```

What survives is what both formats can store. Before you write, call `violations()` to list every value the
target format cannot store. [`../reference/limits.md`](../reference/limits.md) has the full table.

## Switching how the song refers to its voices

The instrument column of a cell names either a sample or an instrument, and each format stores only one of
the two. A song that holds the other kind is refused, so you do that conversion yourself:

```python
from trackmod import flattened, raised

song.model_copy(update={"voices": flattened(song.voices)})   # instruments onto plain samples
song.model_copy(update={"voices": raised(song.voices)})      # samples onto instruments of their own
```

`raised` always works. It gives every sample an instrument that routes every key to it, playing each key at
its own pitch.

`flattened` can fail. A table of samples has no room for an instrument that reaches several samples, or one
that plays a key at another key's pitch, so `flattened` refuses both. It keeps only the routing: envelopes,
fadeout, levels and note behaviors are dropped. Converting a FastTracker 2 song into a format built on
samples is therefore a step you take on purpose, and it can fail. See
[`../reference/model.md`](../reference/model.md).

## Accepting any format

Every module class follows the `TrackerModule` protocol, and every instrument-file class follows
`InstrumentFile`. Use a protocol name in your type hints to accept any format:

```python
from trackmod import TrackerModule

def report(module: TrackerModule) -> str:
    return f"{module.size().total} bytes as {module.extension}"
```

`load_module` returns a `TrackerModule`, so a loop over a mixed folder handles every format the same way.
You reach each file's song, provenance and size report through one interface.

# Taking instruments out of a module

An instrument's keymap names positions in the sample table of the song it belongs to. On its own, then, an
instrument is only half a voice. `InstrumentUnit` holds the other half: the samples its keys reach, numbered
from zero. That is what makes it portable.

```python
from trackmod import extract, units

unit = extract(song.voices, 0)     # the instrument at that position, and the waveforms it plays
held = units(song.voices)          # the same, for every voice in the table
```

`units` works for every format. If a song's cells name samples, TrackMod first raises them onto instruments,
so each sample arrives as an instrument that plays it at the pressed key's pitch. One call therefore reaches
the voices of an `.it`, an `.xm`, a `.mod`, an `.s3m` and a Soundtracker module alike.

`combine` is the way back. It returns exactly the `voices=` table that `Song` takes, with each keymap
renumbered against the samples behind it:

```python
from trackmod import Song, combine

song = Song(name="grafted", channels=4, patterns=..., order=..., voices=combine([unit, other]), playback=...)
```

`Instrument.rerouted(positions)` does the renumbering. It moves the routing and leaves every envelope, level
and behavior unchanged, so an instrument lifted out of one module and written into another sounds the same.
Each unit keeps its own copy of a waveform, even when another unit holds the same one.

## Saving one instrument as a file

Two formats store a single voice as a file of its own: `.iti` and `.xi`. This is what you ship when the
instrument, rather than the song, is the product.

```python
from pathlib import Path

from trackmod import Compliance, ITInstrumentFile, XMInstrumentFile

instrument = ITInstrumentFile.load(Path("piano.iti"))
print(instrument.unit.instrument.name, len(instrument.unit.samples))
print(instrument.size().total)      # how many bytes the file will take
print(instrument.violations())      # values the format cannot store, empty when it is writable

XMInstrumentFile.from_unit(instrument.unit, compliance=Compliance.CANONICAL).save(Path("piano.xi"))
```

The interface matches a module's, so you read both the same way. `InstrumentFile` is the protocol to name
when you want to hold either format. The limits are the format's own, so an instrument can carry the same
values in either container.

Envelope times are measured in ticks, and a tick's length follows the tempo. An `.iti` or `.xi` file stores
no tempo, so record the tempo alongside any instrument you save on its own. See
[`../reference/model.md`](../reference/model.md).

## Emptying a whole folder

```python
from pathlib import Path

from trackmod import Compliance, ITInstrumentFile, load_module, units

sounds = Path("sounds")
for path in Path("modules").iterdir():
    module = load_module(path)
    for index, unit in enumerate(units(module.song.voices)):
        instrument = ITInstrumentFile.from_unit(unit, compliance=Compliance.CANONICAL)
        instrument.save(sounds / f"{path.stem}-{index:02d}{instrument.extension}")
```

## Reading whichever container you are given

A file may hold a whole module, or one voice on its own, in either format. `load_voices` reads them all the
same way, from the contents rather than the name:

```python
from trackmod import load_voices

voices = load_voices(path)
```

You get the voice table the format uses, so the choice of container stops mattering once the file is read.

`parse_voices` takes bytes and an extension, when you already know it, in either upper or lower case.
`EXTENSIONS`, `MODULE_EXTENSIONS` and `INSTRUMENT_EXTENSIONS` list which extensions are read.

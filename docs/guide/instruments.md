# Taking instruments out of a module

An instrument's keymap names positions in the sample table of the song it belongs to, so an instrument on
its own is half a voice. `InstrumentUnit` holds the other half — the samples its keys reach, numbered from
zero — which is what makes it portable.

```python
from trackmod import extract, units

unit = extract(song.voices, 0)     # the instrument at that position, and the waveforms it sounds
held = units(song.voices)          # the same, for every voice the table numbers
```

`units` works whichever way the song addresses its voices. A table whose cells name samples is raised onto
instruments first, so each sample arrives as the instrument sounding it at the pressed key's pitch — which
is what lets one call reach the voices of an `.it`, an `.xm`, a `.mod`, an `.s3m` and a Soundtracker
module alike.

`combine` is the way back: it returns exactly the `voices=` table `Song` takes, with each keymap restated
against the samples behind it.

```python
from trackmod import Song, combine

song = Song(name="grafted", channels=4, patterns=..., order=..., voices=combine([unit, other]), playback=...)
```

The renumbering itself is `Instrument.rerouted(positions)`, which moves the routing and leaves every
envelope, level and behavior as stated — so an instrument lifted out of one module and written into
another sounds what it sounded before. Each unit keeps its own copy of a waveform another unit also holds.

## Writing one instrument as a file

The two formats that keep instrument records also store a single voice as a file of its own — `.iti` and
`.xi` — which is what a producer of sampled instruments ships when the instrument is the product.

```python
from pathlib import Path

from trackmod import Compliance, ITInstrumentFile, XMInstrumentFile

instrument = ITInstrumentFile.load(Path("piano.iti"))
print(instrument.unit.instrument.name, len(instrument.unit.samples))
print(instrument.size().total)      # the file length, counted from the tables
print(instrument.violations())      # every bound the unit breaks, empty when it is writable

XMInstrumentFile.from_unit(instrument.unit, compliance=Compliance.CANONICAL).save(Path("piano.xi"))
```

The surface mirrors a module's, so the two are read the same way, and `InstrumentFile` is the protocol a
caller names to hold one of either format. The bounds are the format's own, so what an instrument can
carry is the same question in either container.

An instrument traveling on its own is worth keeping beside the tempo its envelopes were fitted at: an
`.iti` or an `.xi` carries a curve and no clock to read it by. See
[`../reference/model.md`](../reference/model.md).

## Emptying a whole collection

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

## Reading whichever container a producer ships

A producer picks the container: a whole module, or one voice on its own, in either format. `load_voices`
reads them all the same way, from the bytes rather than the name:

```python
from trackmod import load_voices

voices = load_voices(path)
```

What comes back is the voice table the format that wrote the bytes addresses, so the choice of container
stops mattering at the point the bytes are read. `parse_voices` takes the bytes and an extension where you
already know it, matched in either capitalization; `EXTENSIONS`, `MODULE_EXTENSIONS` and
`INSTRUMENT_EXTENSIONS` state which suffixes are read, so the suffix table lives in one place.

# Taking instruments out of a module

An instrument's keymap points to positions in the sample table of the song it belongs to, so an instrument
alone is only half a voice. `InstrumentUnit` holds the other half: the samples its keys reach, numbered from
zero. That makes it portable.

```python
from trackmod import extract, units

unit = extract(song.voices, 0)     # the instrument at that position, and the waveforms it plays
held = units(song.voices)          # the same, for every voice in the table
```

`units` works for every format. When a song's cells name samples, TrackMod first raises them onto
instruments, so each sample arrives as an instrument that plays it at the pitch of the pressed key. One call
reaches the voices of an `.it`, an `.xm`, a `.mod`, an `.s3m` and a Soundtracker module alike.

`combine` goes the other way. It returns the `voices=` table that `Song` takes, with each keymap renumbered
for the samples behind it:

```python
from trackmod import Song, combine

song = Song(name="grafted", channels=4, patterns=..., order=..., voices=combine([unit, other]), playback=...)
```

`Instrument.rerouted(positions)` does the renumbering. It changes the routing and leaves every envelope,
level and behavior as it was, so an instrument lifted out of one module sounds the same in another. Each
unit keeps its own copy of a waveform, even when another unit holds an identical one.

## Saving one instrument as a file

Two formats can store a single voice as a file of its own: `.iti` and `.xi`. Use these when you want to
share an instrument by itself.

```python
from pathlib import Path

from trackmod import Compliance, ITInstrumentFile, XMInstrumentFile

instrument = ITInstrumentFile.load(Path("piano.iti"))
print(instrument.unit.instrument.name, len(instrument.unit.samples))
print(instrument.size().total)      # how many bytes the file will take
print(instrument.violations())      # values the format cannot store, empty when it is writable

XMInstrumentFile.from_unit(instrument.unit, compliance=Compliance.CANONICAL).save(Path("piano.xi"))
```

An instrument file has the same interface as a module, so you read both the same way. Use `InstrumentFile`
as the type when you want to accept either format. Each file follows the limits of its format, so an
instrument carries the same values in a file as it can inside a module.

Envelope times are counted in ticks, and the length of a tick depends on the tempo. An `.iti` or `.xi` file
has no field for the tempo, so record it yourself next to any instrument you save on its own. See
[`../reference/model.md`](../reference/model.md).

## Saving every instrument in a folder

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

## Reading any kind of file

A file may hold a whole module or a single voice, in either format. `load_voices` reads all of them the same
way, going by the file contents:

```python
from trackmod import load_voices

voices = load_voices(path)
```

You get the voice table that the format uses, so the kind of file no longer matters once it is read.

`parse_voices` reads bytes when you already know the extension, in upper or lower case.

Three frozen sets list what can be read:

| Name | Holds |
|---|---|
| `MODULE_EXTENSIONS` | `.it`, `.xm`, `.mod`, `.s3m` |
| `INSTRUMENT_EXTENSIONS` | `.iti`, `.xi` |
| `EXTENSIONS` | both of the above |

Both Amiga layouts use `.mod`, and TrackMod tells them apart from the bytes when it reads them.

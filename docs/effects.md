# Effects

The effect column is the one part of the model that is format-specific. Everything else in a `Song` —
notes, voices, volumes, samples, envelopes — means the same thing in every format and is written by each
in its own bytes. An `Effect` is different: it holds a **command byte that its own format numbers**.

```python
class Effect(BaseModel):
    command: int    # 0..255
    parameter: int  # 0..255
```

The pair travels together because a tracker reads it together: a parameter means something beside its
command and nowhere else. Impulse Tracker spells "set tempo" as command 20 (`T`), FastTracker 2 as
command 15 (`F`). One song therefore carries effects for one format at a time.

## The shared vocabulary

`trackmod.core.effects.catalog.EffectCatalog` is a protocol naming the intents every format expresses, and
each format implements it. Authoring through a catalogue is what makes the intent portable and the
parameter checked:

```python
from trackmod.trackers.xm.effects.catalog import XM_EFFECTS

builder.place(row, channel, Cell(effect=XM_EFFECTS.note_delay(3)))
```

| Intent | Impulse Tracker | FastTracker 2 | Amiga ProTracker | Scream Tracker 3 |
|---|---|---|---|---|
| `set_speed(ticks)` | `Axx`, `1..255` | `Fxx`, below `0x20` | `Fxx`, below `0x20` | `Axx`, `1..255` |
| `set_tempo(beats_per_minute)` | `Txx`, `32..255` | `Fxx`, at `0x20` and above | `Fxx`, at `0x20` and above | `Txx`, `32..255` |
| `position_jump(order)` | `Bxx` | `Bxx` | `Bxx` | `Bxx` |
| `pattern_break(row)` | `Cxx`, the row itself | `Dxx`, decimal digits | `Dxx`, decimal digits | `Cxx`, decimal digits |
| `note_delay(ticks)` | `SDx` | `EDx` | `EDx` | `SDx` |
| `note_cut(ticks)` | `SCx` | `ECx` | `ECx` | `SCx` |
| `volume_slide(up=…, down=…)` | `Dxy` | `Axy` | `Axy` | `Dxy` |
| `set_panning(position)` | `Xxx`, `0..255` | `8xx`, `0..255` | `8xx`, `0..255` | `Xxx`, `0..255` onto 129 steps |

Every method validates its argument against the room its format's parameter byte leaves, so a delay of 16
raises — which is the class of bug that packing `0xD0 | ticks` by hand invites.

Three rows of that table are worth reading twice.

**Speed and tempo share one command in the Amiga lineage.** `Fxx` sets the ticks per row below the tempo
floor and the beats per minute at or above it, so `set_speed` and `set_tempo` return the same command with
parameters drawn from disjoint ranges. Amiga ProTracker is where that arrangement began and FastTracker 2
kept it whole; Scream Tracker 3 gave each clock a command of its own, `Axx` and `Txx`, which is what
Impulse Tracker inherited.

**Three of the four read a pattern break as decimal digits**, inherited from Amiga ProTracker, which
printed the parameter rather than counting it. Impulse Tracker reads the row itself. The catalogue
converts, so a caller says the row it means:

```python
IT_EFFECTS.pattern_break(16).parameter == 16
XM_EFFECTS.pattern_break(16).parameter == 0x16
```

**A volume slide runs one way.** The parameter packs the up amount into the high nibble and the down
amount into the low one, and a tracker reading both set does something undefined. Every catalogue raises
on the pair.

## The full command set

Beyond the catalogue, each format exposes its native commands as an `IntEnum` —
`trackmod.trackers.it.effects.command.ITEffect` and its `XMEffect`, `MODEffect` and `S3MEffect`
counterparts, each with an `Extended` companion for the sub-commands one command selects with its high
nibble. The format documents tabulate them. Anything outside the shared eight is written by naming the
command directly:

```python
Effect(command=ITEffect.TREMOLO, parameter=0x84)
```

Every one of them carries a `.letter` property giving the character the tracker prints, which is what a
pattern display or a log line wants. Amiga ProTracker prints a hexadecimal digit where the others print a
letter, because its command is one nibble.

**The tempo an effect sets is not the tempo a header holds.** FastTracker 2's header tempo is sixteen bits
and its `Fxx` parameter is eight, so a module can start at tempo 441 and still have no way to change to it
mid-song. `Playback(tempo=441)` is accepted and `XM_EFFECTS.set_tempo(441)` raises. See
[`limits.md`](limits.md).

## Reading effects back

A parser puts whatever command and parameter bytes it finds into an `Effect`, unchanged. Interpreting them
is the caller's business, and the format's command enumeration is what interprets them:

```python
from trackmod.trackers.it.effects.command import ITEffect

effect = pattern.cell(row=4, channel=0).effect
if effect is not None and effect.command == ITEffect.SET_TEMPO:
    tempo = effect.parameter
```

A volume column carries a small effect set of its own beside plain levels — slides, vibrato, panning.
Those are shared: the intents are one vocabulary and each format states which of them its own column
reaches, so they live in the model. See [`volume.md`](volume.md).

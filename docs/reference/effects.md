# Effects

The effect column is the one part of the model that depends on the format. Everything else in a `Song`
(notes, voices, volumes, samples, envelopes) means the same thing in every format, and each format writes
it in its own bytes. An `Effect` is different: it holds a **command byte that its own format numbers**.

```python
class Effect(BaseModel):
    command: int    # 0..255
    parameter: int  # 0..255
```

The command and the parameter travel as a pair, because a tracker reads them together. A parameter has
meaning only beside its command. Impulse Tracker spells "set tempo" as command 20 (`T`), and FastTracker 2
spells it as command 15 (`F`). One song therefore holds effects for one format at a time.

## Shared effects

`trackmod.core.effects.catalog.EffectCatalog` is a protocol that lists the intents every format expresses.
Each format implements it. Writing an effect through a catalog makes the intent portable and checks the
parameter:

```python
from trackmod.trackers.xm.effects.catalog import XM_EFFECTS

builder.place(row, channel, Cell(effect=XM_EFFECTS.note_delay(3)))
```

| Intent | Impulse Tracker | FastTracker 2 | Amiga ProTracker | Scream Tracker 3 | Soundtracker |
|---|---|---|---|---|---|
| `set_speed(ticks)` | `Axx`, `1..255` | `Fxx`, below `0x20` | `Fxx`, below `0x20` | `Axx`, `1..255` | `Fxx`, `1..0x1F` |
| `set_tempo(beats_per_minute)` | `Txx`, `32..255` | `Fxx`, at `0x20` and above | `Fxx`, at `0x20` and above | `Txx`, `32..255` | — |
| `position_jump(order)` | `Bxx` | `Bxx` | `Bxx` | `Bxx` | `Bxx` |
| `pattern_break(row)` | `Cxx`, the row itself | `Dxx`, decimal digits | `Dxx`, decimal digits | `Cxx`, decimal digits | `Dxx`, decimal digits |
| `note_delay(ticks)` | `SDx` | `EDx` | `EDx` | `SDx` | — |
| `note_cut(ticks)` | `SCx` | `ECx` | `ECx` | `SCx` | — |
| `volume_slide(up=…, down=…)` | `Dxy` | `Axy` | `Axy` | `Dxy` | — |
| `set_panning(position)` | `Xxx`, `0..255` | `8xx`, `0..255` | `8xx`, `0..255` | `Xxx`, `0..255` onto 129 steps | — |

Every method checks its argument against the room the format's parameter byte leaves, so a delay of 16
raises. Packing `0xD0 | ticks` by hand invites exactly that kind of bug. A dash marks an intent the format
has no command for. Asking for one raises at once, and the error names the command that would carry it in a
format that has one.

Three rows of that table need a closer look.

**Speed and tempo share one command in the Amiga lineage.** `Fxx` sets the ticks per row below the tempo
floor and the beats per minute at or above it. So `set_speed` and `set_tempo` return the same command, with
parameters in separate ranges. Amiga ProTracker began that arrangement and FastTracker 2 kept it unchanged.
Scream Tracker 3 gave each clock its own command, `Axx` and `Txx`, and Impulse Tracker inherited that.

**Four of the five read a pattern break as decimal digits.** Amiga ProTracker began this by reading each
nibble of the parameter as a printed digit. Impulse Tracker reads the row itself. The catalog converts, so
a caller gives the row it means:

```python
IT_EFFECTS.pattern_break(16).parameter == 16
XM_EFFECTS.pattern_break(16).parameter == 0x16
```

**A volume slide runs one way.** The parameter packs the up amount into the high nibble and the down
amount into the low nibble. A tracker that reads both set does something undefined, so every catalog
raises on the pair.

## Native commands

Each format also exposes its native commands as an `IntEnum`:
`trackmod.trackers.it.effects.command.ITEffect` and its `XMEffect`, `MODEffect`, `S3MEffect` and
`STEffect` counterparts. Four of the formats have cells that hold an extended command, and each of them has
an `Extended` companion enum for the sub-commands that one command selects with its high nibble.
Soundtracker has only its seven commands. The format documents list them in tables. To write a command
outside the shared eight, name it directly:

```python
Effect(command=ITEffect.TREMOLO, parameter=0x84)
```

Each command has a `.letter` property that returns the character the tracker prints for it. A pattern
display or a log line can use it. Amiga ProTracker prints a hexadecimal digit where the others print a
letter, because its command is one nibble.

**A header can hold a tempo that the effect column cannot reach.** FastTracker 2's header tempo is sixteen
bits wide and its `Fxx` parameter is eight bits wide. A module that starts at tempo 441 keeps that clock
for as long as it holds it. `Playback(tempo=441)` is accepted and `XM_EFFECTS.set_tempo(441)` raises. See
[`limits.md`](limits.md).

## Reading effects from a song

A parser puts the command and parameter bytes it finds into an `Effect` unchanged. Interpreting them is the
caller's job, and the format's command enumeration does the interpreting:

```python
from trackmod.trackers.it.effects.command import ITEffect

effect = pattern.cell(row=4, channel=0).effect
if effect is not None and effect.command == ITEffect.SET_TEMPO:
    tempo = effect.parameter
```

A volume column holds a small effect set of its own beside plain levels: slides, vibrato and panning. That
set is shared. The intents form one vocabulary, and each format records which of them its own column
reaches, so the set lives in the model. See [`volume.md`](volume.md).

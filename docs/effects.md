# Effects

The effect column is the one part of the model that is format-specific. Everything else in a `Song` —
notes, instruments, volumes, samples, envelopes — means the same thing in both formats and is written by
each in its own bytes. An `Effect` is different: it holds a **command byte that its own format numbers**.

```python
class Effect(BaseModel):
    command: int    # 0..255
    parameter: int  # 0..255
```

The pair travels together because a tracker reads it together; a parameter without its command means
nothing. Impulse Tracker spells "set tempo" as command 20 (`T`), FastTracker 2 as command 15 (`F`). One
song therefore carries effects for one format at a time.

## The shared vocabulary

`trackmod.core.effects.catalog.EffectCatalog` is a protocol naming the intents both formats express:

| Method | Intent |
|---|---|
| `set_speed(ticks)` | How many ticks each row lasts |
| `set_tempo(beats_per_minute)` | The tick rate |
| `position_jump(order)` | Continue at an order-list position |
| `pattern_break(row)` | End the pattern, continue at a row of the next order |
| `note_delay(ticks)` | Delay this cell's note into the row |
| `note_cut(ticks)` | Silence this channel partway through the row |
| `volume_slide(up=…, down=…)` | Slide the channel volume, one nibble per tick |
| `set_panning(position)` | Place the channel on the shared `0..255` field |

Each format implements it: `trackmod.it.effects.catalog.IT_EFFECTS` and
`trackmod.xm.effects.catalog.XM_EFFECTS`. Authoring through a catalogue rather than by writing byte
literals is what makes the intent portable and the parameter checked:

```python
from trackmod.xm.effects.catalog import XM_EFFECTS

builder.place(row, channel, Cell(effect=XM_EFFECTS.note_delay(3)))
```

Every method validates its argument against the room its format's parameter byte leaves. A delay of 16
raises rather than silently colliding with the next sub-command, which is the class of bug that packing
`0xD0 | ticks` by hand invites.

Beyond the catalogue, each format exposes its **full** native command set as an `IntEnum` —
`trackmod.it.effects.command.ITEffect` and `trackmod.xm.effects.command.XMEffect`, each with an
`ITExtended` / `XMExtended` companion for the sub-commands that one command selects with its high
nibble. Anything outside the shared eight is written by naming the command directly:

```python
Effect(command=ITEffect.TREMOLO, parameter=0x84)
```

Both enumerations carry a `.letter` property giving the character the tracker prints, which is what a
pattern display or a log line wants.

## Where the two spellings differ

**Speed and tempo share one command in FastTracker 2.** `Fxx` sets the ticks per row below the tempo
floor and the beats per minute at or above it, so the catalogue's `set_speed` and `set_tempo` return the
same command with parameters drawn from disjoint ranges — `1..31` and `32..255`. Impulse Tracker
separates them into `Axx` and `Txx`.

**FastTracker 2 reads its pattern break as decimal digits.** A break to row 16 stores `0x16`, not
`0x10`, inherited from the ProTracker command it descends from. The catalogue converts, so a caller says
the row it means:

```python
IT_EFFECTS.pattern_break(16).parameter == 16
XM_EFFECTS.pattern_break(16).parameter == 0x16
```

**A volume slide runs one way.** The parameter packs the up amount into the high nibble and the down
amount into the low one, and a tracker reading both set does something undefined. Both catalogues raise
rather than emit it.

**The tempo an effect sets is not the tempo a header holds.** FastTracker 2's header tempo is sixteen
bits and its `Fxx` parameter is eight, so a module can start at tempo 441 and still have no way to
change to it mid-song. `XM_EFFECTS.set_tempo(441)` raises; `Playback(tempo=441)` does not. See
[`limits.md`](limits.md).

## Reading effects back

A parser puts whatever command and parameter bytes it finds into an `Effect`, unchanged. Interpreting
them is the caller's business, and the format's command enumeration is what interprets them:

```python
from trackmod.it.effects.command import ITEffect

effect = pattern.cell(row=4, channel=0).effect
if effect is not None and effect.command == ITEffect.SET_TEMPO:
    tempo = effect.parameter
```

FastTracker 2's volume column carries its own small effect set beside plain levels — slides, vibrato,
panning. Only the level range `0x10..0x50` maps onto the shared model's `volume`, so a parser reads
those as levels and leaves the rest out of the cell rather than misreading a slide as a loudness.

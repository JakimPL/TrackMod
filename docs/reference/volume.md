# The volume column

Every cell of the model has a volume column. Each format that stores one uses it for more than a level. A
byte in one range sets how loud a note plays. A byte in another range slides that level, bends the pitch,
sets the panning or starts a vibrato. The ranges and the amounts differ between formats, but the intents
are the same handful. The vocabulary is therefore shared, and each format records in data which intents its
own column reaches.

[`effects.md`](effects.md) works differently. An effect holds a command byte that its own format numbers,
so a song holds effects for one format at a time. A volume-column entry names an intent that every format
knows, so it travels between formats wherever both ends name it.

## What a cell holds

`Cell.volume` is a level, an entry that acts on the playing voice, or absent:

```python
Cell(volume=48)                                                        # a level
Cell(volume=VolumeCommand(effect=VolumeEffect.VIBRATO_DEPTH, amount=4))
Cell()                                                                 # the column states nothing
```

`trackmod.core.volumes.command.VolumeEffect` names the twelve intents that the columns state between them,
and `VolumeCommand` pairs one intent with its amount. `VolumeValue = Volume | VolumeCommand` is what the
column holds, just as `NoteValue = Note | NoteCommand` is what the note column holds.

**Each amount is stated on the grid of the format's own column.** Impulse Tracker counts a slide in ten
steps and FastTracker 2 counts it in sixteen. Converting between them would cost a file the byte-for-byte
round trip this library is built on. So the amount is kept as the column stores it, and each format's
specification gives the room it leaves. [`limits.md`](limits.md) grades the amount against that room.

## How the model stores the column

A pattern is five aligned planes of `numpy.int16`, one plane per column, and the volume column is one of
them. The plane holds a level in `0..64`. Above it, each effect has one run of consecutive codes, so a single
integer holds either kind. The note column does the same with its commands above the key range.
`trackmod.core.volumes.codec` is the pair that reads and writes that numbering, and `trackmod.spec.volumes`
defines it. Each run is a whole byte wide, which covers every amount a one-byte column can hold, so the
shared numbering leaves every format's field enough room.

## What each format's column supports

Each format describes its own column once, as data. Its parser, its packer and its capacity table all read
that one description. The byte runs are in the format documents, next to the cell that holds them. The
table below shows which intents each column names and the amount it counts them in.

| Intent | Impulse Tracker | FastTracker 2 | Amiga ProTracker | Scream Tracker 3 | Soundtracker |
|---|---|---|---|---|---|
| Fine volume up | `0..9` | `0..15` | — | — | — |
| Fine volume down | `0..9` | `0..15` | — | — | — |
| Volume slide up | `0..9` | `0..15` | — | — | — |
| Volume slide down | `0..9` | `0..15` | — | — | — |
| Pitch slide up | `0..9` | — | — | — | — |
| Pitch slide down | `0..9` | — | — | — | — |
| Portamento | `0..9` | `0..15` | — | — | — |
| Vibrato depth | `0..9` | `0..15` | — | — | — |
| Vibrato speed | — | `0..15` | — | — | — |
| Panning | `0..64` | `0..15` | — | `0..64` | — |
| Panning slide left | — | `0..15` | — | — | — |
| Panning slide right | — | `0..15` | — | — | — |

Impulse Tracker's column and FastTracker 2's share seven of the twelve intents. They are the only two columns
that hold more than a level and a panning position. A song that uses only those seven carries its volume
column into either format, at an amount both columns count. One counts a rate in ten steps and the other in
sixteen, so nine is the largest portable amount. Panning is coarser in one of them than in the other, and
[`formats/README.md`](../formats/README.md) collects that with the other places the formats disagree.

Scream Tracker 3's column holds a level and a panning position, both counted to `0..64`, which is the full
grid a level travels on. Amiga ProTracker's cells hold a note, a sample and an effect, so a level travels
there as the `Cxx` command its lineage uses for it, and a cell that arrives with a volume in it is refused
by name.

## When a column cannot hold a value

A column can fail to hold a value in two ways, and [`limits.md`](limits.md) keeps them apart.

An **amount past its run** is a quantity. It is graded against `Capability.VOLUME_COMMAND` or
`Capability.VOLUME_PANNING` and reported as a violation:

```
pattern 0: volume_command is 10, outside 0..9 (structural)
```

An **effect the column has no run for** is content that the format has no encoding for, so it raises where
it is met. A pitch slide written as FastTracker 2 and a vibrato speed written as Impulse Tracker are
examples:

```
ValueError: the volume column has no run for VIBRATO_SPEED
```

## Bytes that mean nothing

Every column has gaps: Impulse Tracker between `125..127` and above `212`, FastTracker 2 between `0x01` and
`0x0F` and again between `0x51` and `0x5F`, Scream Tracker 3 between `65` and `127` and above `192`. A byte
in a gap means something this vocabulary has no term for, so the column reads as absent. The parse reports
what it met, once for a whole pattern:

```
UnnamedByteWarning: bytes this format leaves unnamed, read as absent: volume 213
```

The note column reads the same way, for the same reason. Impulse Tracker numbers keys up to 119 and keeps
its commands at the top of the byte range. FastTracker 2 numbers eight octaves from one and keeps `97` for
a key off. Scream Tracker 3 spells a key as an octave over a semitone, and a semitone nibble past the
twelfth means nothing. Amiga ProTracker holds a period that lands on no key it tabulates. The values in
between belong to none of those vocabularies.

`trackmod.binary.warnings.UnnamedByteWarning` is what a caller filters on to raise, silence or collect
those warnings. Gathering them and warning once follows the choice `Checklist` already makes for
violations: a file that goes past what this library reads shows it in cell after cell, and one report says
as much.

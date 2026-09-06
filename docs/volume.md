# The volume column

Every cell of the model carries a volume column, and each format that stores one spends it on more than a
level. A byte in one range sets how loud a note plays; a byte in another slides that level, bends the
pitch, sets the panning or starts a vibrato. The ranges differ between the formats and so do the amounts
they carry, but the intents are the same handful — so the vocabulary is shared, and each format states in
data which of it its own column reaches.

This is the opposite arrangement from [`effects.md`](effects.md). An effect holds a command byte its own
format numbers, so a song carries effects for one format at a time. A volume-column entry names an intent
every format knows, so it travels between them wherever both ends name it.

## What a cell holds

`Cell.volume` is either a level, an entry acting on the playing voice, or absent:

```python
Cell(volume=48)                                                        # a level
Cell(volume=VolumeCommand(effect=VolumeEffect.VIBRATO_DEPTH, amount=4))
Cell()                                                                 # the column states nothing
```

`trackmod.core.volumes.command.VolumeEffect` names the twelve intents the columns state between them, and
`VolumeCommand` pairs one with the amount it carries. `VolumeValue = Volume | VolumeCommand` is what the
column holds, the way `NoteValue = Note | NoteCommand` is what the note column holds.

**The amount is stated on the grid the format's own column counts in.** Impulse Tracker counts a slide in
ten steps and FastTracker 2 in sixteen, and converting between them would cost a file the byte-for-byte
round trip this library is built on — so the amount is carried as the column stores it, and each format's
specification names the room it leaves. [`limits.md`](limits.md) grades it there.

## One integer per column

A pattern is five aligned planes of `numpy.int16`, one per column, and the volume column is one of them.
The plane holds a level in `0..64` and continues past it, one run of codes per effect, so a single integer
holds either kind — exactly what the note column does with its commands past the key range.
`trackmod.core.volumes.codec` is the pair that reads and writes that numbering, and `trackmod.spec.volumes`
states it. A run is a whole byte wide, which is every amount a one-byte column can state, so no format's
field is cramped by the shared numbering.

## What each column reaches

Each format states its own column once, as data, and its parser, its packer and its capacity table read
that one statement. The byte runs live in the format documents, beside the cell that carries them; what
follows is which intents each column names, and the amount it counts them in.

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

Seven of the twelve are shared by Impulse Tracker's column and FastTracker 2's, the two that spell more
than one effect between them. A song using only those seven carries its volume column into either, at an
amount both columns count — one counts a rate in ten steps and the other in sixteen, so nine is as far
as a portable amount reaches. Panning is coarser still in one direction than the other, and
[`formats/README.md`](formats/README.md) collects that with the other places the formats disagree.

Scream Tracker 3 spends its column on a level and a panning position, both counted to `0..64`, which is
the full grid a level travels on. Amiga ProTracker's cells carry a note, a sample and an effect, so a
level travels there as the `Cxx` command its lineage spells one with, and a cell arriving with a volume in
it is refused by name.

## What a column refuses

The two ways a column can fail to state something are the two [`limits.md`](limits.md) keeps apart.

An **amount past its run** is a quantity, graded against `Capability.VOLUME_COMMAND` or
`Capability.VOLUME_PANNING` and reported as a violation:

```
pattern 0: volume_command is 10, outside 0..9 (structural)
```

An **effect the column has no run for** — a pitch slide written as FastTracker 2, a vibrato speed written
as Impulse Tracker — is content that format has no encoding for, so it raises where it is met:

```
ValueError: the volume column has no run for VIBRATO_SPEED
```

## A byte naming nothing

Every column leaves gaps: Impulse Tracker between `125..127` and above `212`, FastTracker 2 between `0x01`
and `0x0F`, Scream Tracker 3 between `65` and `127` and above `192`. A file carrying one of those states
something this vocabulary has no term for, so the column reads as absent and the parse reports what it
met, once for a whole pattern:

```
UnnamedByteWarning: bytes this format leaves unnamed, read as absent: volume 213
```

The note column reads the same way, for the same reason: Impulse Tracker numbers keys to 119 and keeps its
commands at the top of the byte range, FastTracker 2 numbers eight octaves from one and keeps `97` for a
key off, Scream Tracker 3 spells a key as an octave over a semitone and leaves a semitone nibble past the
twelfth naming nothing, and Amiga ProTracker holds a period that lands on no key it tabulates. The values
between name nothing any of those vocabularies holds.

`trackmod.binary.warnings.UnnamedByteWarning` is what a caller filters on to raise, silence or collect
those. Gathering them and warning once is the choice `Checklist` already makes for violations: a file
reaching past what this library reads states it in cell after cell, and one report says as much.

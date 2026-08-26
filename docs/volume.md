# The volume column

Every cell of a pattern carries a volume column, and both formats spend it on more than a level. A byte
in one range sets how loud a note plays; a byte in another slides that level, bends the pitch, sets the
panning or starts a vibrato. The ranges differ between the formats and the amounts they carry differ
with them, but the intents are the same handful — so the vocabulary is shared and each format states in
data which of it its own column reaches.

This is the opposite arrangement from [`effects.md`](effects.md). An effect holds a command byte its own
format numbers, so a song carries effects for one format at a time. A volume-column entry names an
intent both formats know, so it travels between them wherever both name it.

## What a cell holds

`Cell.volume` is either a level, an entry acting on the playing voice, or absent:

```python
Cell(volume=48)                                                        # a level
Cell(volume=VolumeCommand(effect=VolumeEffect.VIBRATO_DEPTH, amount=4))
Cell()                                                                 # the column states nothing
```

`trackmod.core.volumes.command.VolumeEffect` names the twelve intents the two columns state between
them, and `VolumeCommand` pairs one with the amount it carries. `VolumeValue = Volume | VolumeCommand`
is what the column holds, the way `NoteValue = Note | NoteCommand` is what the note column holds.

**The amount is stated on the grid the format's own column counts in.** Impulse Tracker counts a slide
in ten steps and FastTracker 2 in sixteen, and converting between them would cost a file the byte-for-byte
round trip this library is built on — so the amount is carried as the column stores it, and each format's
specification names the room it leaves. `limits.md` grades it there.

## One integer per column

A pattern is five aligned planes of `numpy.int16`, one per column, and the volume column is one of them.
The plane holds a level in `0..64` and continues past it, one run of `AMOUNT_COUNT` codes per effect, so
a single integer holds either kind — exactly what the note column does with its commands past the key
range. `trackmod.core.volumes.codec` is the pair that reads and writes that numbering, and
`trackmod.spec.volumes` states it.

A run is a whole byte wide, which is every amount a one-byte column can state, so no format's field is
cramped by the shared numbering.

## What each format's column reaches

Each column is stated once as data, in `trackmod.trackers.<format>.spec.volume`, and the parser, the
packer and the capacity table read that one table.

**Impulse Tracker.** A mask bit says whether the column is present at all, so every byte in it means
something:

| Bytes | States | Amounts |
|---|---|---|
| `0..64` | a level | `0..64` |
| `65..74` / `75..84` | fine volume up / down | `0..9` |
| `85..94` / `95..104` | volume slide up / down | `0..9` |
| `105..114` / `115..124` | pitch slide down / up | `0..9` |
| `128..192` | panning | `0..64` |
| `193..202` | portamento | `0..9` |
| `203..212` | vibrato depth | `0..9` |

**FastTracker 2.** A cell stating every column writes a byte here whatever it holds, so one value stands
for an absent volume:

| Bytes | States | Amounts |
|---|---|---|
| `0x00` | no volume | — |
| `0x10..0x50` | a level | `0..64` |
| `0x60..0x6F` / `0x70..0x7F` | volume slide down / up | `0..15` |
| `0x80..0x8F` / `0x90..0x9F` | fine volume down / up | `0..15` |
| `0xA0..0xAF` / `0xB0..0xBF` | vibrato speed / depth | `0..15` |
| `0xC0..0xCF` | panning | `0..15` |
| `0xD0..0xDF` / `0xE0..0xEF` | panning slide left / right | `0..15` |
| `0xF0..0xFF` | portamento | `0..15` |

Impulse Tracker names ten of the twelve intents and FastTracker 2 the other ten; eight are shared, and a
song using only those eight carries its volume column into either format.

## What a column refuses

The two ways a column can fail to state something are the two `limits.md` keeps apart.

An **amount past its run** is a quantity, graded against `Capability.VOLUME_COMMAND` or
`Capability.VOLUME_PANNING` and reported as a violation:

```
pattern 0: volume_command is 10, outside 0..9 (structural)
```

An **effect the column has no run for** — a pitch slide written as FastTracker 2, a vibrato speed
written as Impulse Tracker — is content that format has no encoding for, so it raises where it is met:

```
ValueError: the volume column has no run for VIBRATO_SPEED
```

## A byte naming nothing

Both columns leave gaps: Impulse Tracker between `125..127` and above `212`, FastTracker 2 between
`0x01` and `0x0F`. A file carrying one of those states something this vocabulary has no term for, so the
column reads as absent and the parse reports what it met, once for a whole pattern:

```
UnnamedByteWarning: bytes this format leaves unnamed, read as absent: volume 213
```

`trackmod.binary.warnings.UnnamedByteWarning` is what a caller filters on to raise, silence or collect
those. Gathering them and warning once is the choice `Checklist` already makes for violations: a file
reaching past what this library reads states it in cell after cell, and one report says as much.

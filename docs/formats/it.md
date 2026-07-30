# Impulse Tracker (`.it`)

Written by `trackmod.trackers.it.writer.write_module`, read by `trackmod.trackers.it.parser.ModuleReader`, bound together
by `trackmod.trackers.it.module.ITModule`.

## File shape

The file is found by **offset tables**. The header declares how many instruments, samples and patterns
there are; three tables of 32-bit offsets follow the order list, one entry per item, and each points at
where that item's record sits. Sections may therefore be laid out in any order, and `trackmod` lays them
out like this:

```
IMPM file header                            192 bytes
order list                                  one byte per position, then 0xFF
instrument offsets, sample offsets, pattern offsets    4 bytes each
instrument headers                          554 bytes each
sample headers                              80 bytes each
packed patterns                             8-byte header + cell stream
sample frames                               pointed at by each sample header
song message                                pointed at by the file header, when there is one
```

Sample frames sit last among the sections the offset tables reach, because a sample header carries a
pointer to them, so where they land has to be resolved before the headers that point at them are built.
`trackmod.trackers.it.writer.lay_out` does exactly that and nothing else. The song message closes the
file, past everything those tables address.

`trackmod.trackers.it.spec.storage.IT_STORAGE` states those sizes as the cost table a caller budgets
against, with each section's four-byte offset entry folded into the section it points at — so one more
sample costs 84 bytes of records before its frames. `trackmod.trackers.it.sizing` reads that table, which
is what keeps it agreeing with the layout above.

Each section carries its own tag: `IMPM` opens the file, `IMPI` each instrument, `IMPS` each sample.

The header's order table ends with `0xFF`; `0xFE` marks a separator. Neither is a playable position, so
the parser drops both and `OrderList` holds only positions that play.

The header reserves two 64-byte tables for per-channel panning and volume, which is the format's own
channel count rather than the song's. `ITSettings` carries them at that width, along with the global
volume, mix volume, panning separation and the song-wide flags.

### The song message

The format attaches free text to a module: the header states its length at offset 54 and points at it
with a 32-bit offset at 56, and bit 0 of `special` at offset 46 says a block is attached at all.
`ITSettings.message` carries it, and `MessageBlock` is where the writer settles the three fields
together — a module attaching no message states a zero offset, a zero length and a clear switch.

The text is terminated rather than padded, so a reader stops at the terminator inside the length the
header reserves. Impulse Tracker's own editor keeps 8000 bytes and the field reaches 65535, which is the
canonical and structural pair `message_bytes` states. Lines are separated by `\r`, which is what a
tracker showing the message expects; the block is stored as given, so whatever a producer writes into it
comes back out.

## Packed patterns

A pattern is a stream of channel markers, and this is where the format spends its cleverness.

Each row lists **only the channels that carry something** and ends with a `0x00` terminator, so a silent
channel costs nothing at all. A pattern of pure silence is one byte per row.

A listed channel is announced by the byte `channel + 1`, with `0x80` set when a mask byte follows. The
mask names which columns are present:

| Bit | Meaning |
|---|---|
| `0x01` | A note byte follows |
| `0x02` | An instrument byte follows |
| `0x04` | A volume byte follows |
| `0x08` | A command and parameter byte follow |
| `0x10` | Repeat the note this channel last stated |
| `0x20` | Repeat the instrument |
| `0x40` | Repeat the volume |
| `0x80` | Repeat the effect |

Every channel keeps a **memory** of what it last stated and of the mask it last used. A column that
repeats costs a bit instead of a byte; a mask identical to the channel's previous one is left out
entirely. A channel holding steady therefore settles to a single byte per row, and re-stating a note
still re-triggers the sample.

### How wide a pattern is

The format states a channel count nowhere — not in the file header, not in a pattern's own header — so
the width comes back out of the cell stream, as the widest channel any row lists. A song holding channels
in reserve therefore comes back narrower than it went in: a stereo pair rounded up to, a part yet to be
written, or a track whose voices never all sound at once.

`trackmod.trackers.it.patterns.width` closes that gap. Where the grid leaves the widest channel silent,
the opening row names it with a **mask over no columns** — two bytes, `0x80 | channels` and `0x00` — which
decodes as the silence already sitting there. `Song.channels` then survives a round trip, and the size
model counts the same two bytes the packer spends.

Readers deriving a width from content read exactly the module they read before, since the cell states no
column: libopenmpt reports such a file at the width its notes reach and renders it byte for byte the same.

`trackmod.trackers.it.patterns.packer` writes that stream and `trackmod.trackers.it.patterns.parser` reads it.
`trackmod.trackers.it.patterns.sizing.packed_bytes` computes its length without building it, a whole channel at a
time: because the reuse bits depend only on that channel's previous stated value, each column reduces to
one run-length comparison. The two are pinned to each other by test.

**Instrument numbers in the cell stream are one-based.** Zero is what a cell writes to leave a channel on
the instrument it already carries, so the writer stores `index + 1` and the parser subtracts it. A
zero-based write produces a module that a player renders as silence while every round trip through the
library's own parser still passes — which is how this was found, and why the probes in
[`limits.md`](../limits.md) render through a real player rather than trusting the parser alone.

## Notes

Impulse Tracker numbers its keyboard from C-0 exactly as the shared model does, so a key is stored as
its own number. The commands sit at the top of the byte range: fade `253`, cut `254`, off `255`.

## Samples

`SAMPLE_HEADER` is 80 bytes. The rate is stored as **C5Speed**: the frequency in hertz at which the
sample sounds when key C-5 is pressed, which is exactly the shared model's `Sample.rate`, written
straight out.

Frames are stored **absolutely** — signed 8- or 16-bit amplitudes, no differencing. Both a loop and a
sustain loop are supported, each optionally ping-pong, with the flags in the header's flag byte.

The panning byte reserves its high bit as an enable switch and stores a position on `0..64`, so a
sample's shared `0..255` panning is scaled on the way in and back out. `gain` maps onto the header's
global volume, which is the per-sample multiplier FastTracker 2 has no equivalent for.

## Instruments

`INSTRUMENT_HEADER` is 554 bytes and carries **three** envelopes — volume, panning and pitch — at offsets
`0x130`, `0x182` and `0x1D4`, each with up to 25 nodes and its own flag byte for enabled, loop, sustain,
carry and filter.

The keymap is 120 pairs of `(played note, sample number)`. Sample numbers are one-based, so zero
silences a key; an unmapped key still names its own pitch, which is the identity mapping a tracker writes
for an instrument with nothing routed yet.

## Fadeout

`trackmod.trackers.it.fade` binds the shared fade to this format's counter, which is **1024**: a fading
voice loses `fadeout` from it every tick, so it falls silent after `1024 / fadeout` ticks. Impulse
Tracker's own editor counts a fadeout to 128, whose eight ticks are the quickest fade it states — the
same eight ticks FastTracker 2 reaches through a number 32 times larger.

The fade starts where the volume envelope **ends**, so an instrument with no volume envelope begins
fading at the note off and one whose curve runs on for another 8000 ticks fades that much later. Both
were verified by rendering. This is the one place the two formats disagree about a shared field, and it
is why a released voice is worth playing down by the curve rather than by the fade when one song is
written to both.

## One instrument on its own (`.iti`)

The same records make a file of one instrument, written by
`trackmod.trackers.it.instruments.writer.write_instrument_file` and bound by
`trackmod.trackers.it.instrument_file.ITInstrumentFile`:

```
IMPI instrument header                      554 bytes
IMPS sample headers                         80 bytes each
sample frames                               pointed at by each sample header
```

The header's sample count is what says how many headers follow it, so a reader finds each one by
arithmetic where a module would consult an offset table. Each sample pointer is still counted from the
start of the file, which is why `trackmod.trackers.it.samples.parser.read_sample` serves both containers.
The keymap's one-based sample numbers name the samples stored here, in the order they are stored.

```python
from trackmod.core.instruments.transfer import extract
from trackmod.trackers.it.instrument_file import ITInstrumentFile
from trackmod.limits.compliance import Compliance

unit = extract(song, 0)
ITInstrumentFile.from_unit(unit, compliance=Compliance.CANONICAL).save(Path("piano.iti"))
```

## Timing

`trackmod.trackers.it.timing` binds the shared clock to this format's speed (`1..255`) and tempo (`32..255`)
ranges. The one-byte tempo is the constraint that matters: at 44100 Hz and speed 1 the shortest
whole-frame row this format reaches is 441 frames.

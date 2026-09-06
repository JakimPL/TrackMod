# FastTracker 2 (`.xm`)

FastTracker 2 was written by Fredrik Huss and Magnus Högdahl of Triton and released in 1994 for MS-DOS.
An `.xm` file holds a song's patterns, its order list and its instruments — and the instrument is the
unit this format thinks in: a named voice that routes each of 96 keys onto one of its own samples, with
envelopes and a fadeout of its own.

A file is one concatenation read front to back, and that single decision shapes everything below.

## At a glance

| | |
|---|---|
| Tracker | FastTracker 2, Triton, 1994 |
| Byte order | little-endian |
| A cell's instrument column names | an instrument |
| Sections are found by | walking sizes, front to back |
| Channels | 1..32 canonical, 1..127 extended, 1..65535 stored |
| Pattern rows | 1..256 canonical, 1..1024 extended, 1..65535 stored |
| Note range | 8 octaves, shared keys 0..95 |
| Waveform storage | 8- or 16-bit signed, stored as differences |
| One instrument on its own | `.xi` |

## File shape

```
"Extended Module: " header     80 bytes, its own length restated at offset 60
order list                     256 bytes, whatever the song plays
pattern 0..n                   9-byte header, then the packed cell stream
instrument 0..n                header, its sample headers, then its waveforms
```

The `header_size` field at offset 60 counts from that offset onward and covers the rest of the header
together with the whole order list, so a reader seeks to `60 + header_size` for the first pattern. An
instrument is self-contained: its header, its sample headers, then its waveforms, in header order.

## Order list

The header states `order_count` played positions at offset 64 and a `restart_position` at offset 66.
The list occupies its full 256 bytes whatever the count, and each entry is one byte naming a pattern.

A restart position past the last played entry is drawn back inside the list, and an entry naming a
pattern the file leaves out is dropped. Both are reported.

## Patterns

A 9-byte pattern header states its own length, a packing type, the row count and the packed byte count.
Every cell of every row is stored and nothing terminates a row, so a reader takes exactly `rows ×
channels` cells. **Each cell is complete in itself**, so a reader takes it on its own terms and the
grid is exactly what the stream states.

The first byte of a cell decides how it is read:

- **High bit set** — the byte is a mask, and only the columns it names follow, in this order:

  | Bit | Column |
  |---|---|
  | `0x01` | note |
  | `0x02` | instrument |
  | `0x04` | volume |
  | `0x08` | effect command |
  | `0x10` | effect parameter |

- **High bit clear** — the byte *is* the note, and all five columns follow in full.

A cell stating all five columns costs five bytes in the second form against six in the first, so a full
cell drops its mask; a cell stating nothing costs the one byte its empty mask occupies, so a silent
pattern costs `rows × channels` bytes. A stream ending before the cells the header counts leaves the
rest of the grid silent, which is reported.

### The note column

Notes sit one **above** the shared numbering: key `k` is byte `k + 1`, byte `97` is a key off, and the
eight octaves this format numbers are shared keys `0..95`. Bytes 98 to 255 read as an absent note.

### The instrument column

The column names an **instrument**, one-based: byte `n` is instrument `n - 1`, and `0` leaves the channel
on the instrument it already carries. A cell naming an instrument past the table the file holds reads
the same way, and it is reported.

### The volume column

The byte stores a level as `0x10 + level` for levels `0..64`, and spends the rest of its range on ten
effects, each occupying a run of sixteen values:

| Run | Intent | Run | Intent |
|---|---|---|---|
| `0x60` | volume slide down | `0xB0` | vibrato depth |
| `0x70` | volume slide up | `0xC0` | panning |
| `0x80` | fine volume down | `0xD0` | panning slide left |
| `0x90` | fine volume up | `0xE0` | panning slide right |
| `0xA0` | vibrato speed | `0xF0` | portamento |

`0x00` is what a cell stating every column writes where it holds no volume, so that byte reads as an
absence, and the bytes below the level range read the same way — reported once for a whole pattern. See
[`volume.md`](../volume.md).

## Instruments

The 263-byte instrument header states its own length, a 22-byte name, a sample count, and then a body:
a 96-byte keymap naming one sample position per key, two envelopes, an auto-vibrato and a fadeout.

Each instrument carries **its own copies** of the samples its keys reach, so a sample two instruments
both play is written twice and counted twice. Reading a module back gives one instrument per group of
samples, and a song whose two instruments shared one sample comes back holding two.

A stored sample carries one transposition, so every key routed to it agrees on the pitch it sounds; a
keymap shifting one key of a sample differently from another asks for a field this format keeps on the
sample, and is refused.

An instrument owning no samples is written in the **29-byte** short header, which stops after the sample
count. Those 29 bytes are the opening of the long form, which is what makes a placeholder slot cheap.

### Envelopes

Two envelopes, volume and panning, of at most 12 points each, values `0..64`. Their point tables sit at
fixed offsets in the instrument header — volume from 129, panning from 177 — with the counts, sustain
points, loop bounds and flags behind them. The flag bits are `0x01` enabled, `0x02` sustain, `0x04` loop.

The sustain is a **single point**, so an envelope sustaining across a span of points is refused. A loop
or sustain stated outside its own points is drawn back inside them, and points stated out of order are
held at the tick before them; both are reported.

### Fadeout

A fading voice loses `fadeout` from a counter of **32768** every tick, so it falls silent after
`32768 / fadeout` ticks. The field is sixteen bits wide, and the tracker's own editor counts to `0xFFF`,
whose eight ticks are the quickest fade it states.

The fade begins at the **key off**, wherever the volume envelope has reached, so a fade to state is a
fade with a curve to state it against.

## Samples

The 40-byte sample header states a length, a loop begin and a loop length, a volume, a finetune, a type
byte, a panning, a relative note and a 22-byte name. **The lengths count bytes**, so a 16-bit sample's
stored length is twice its frame count. The type byte carries the loop mode in its low
two bits — `0` none, `1` forward, `2` ping-pong — and the 16-bit flag at `0x10`.

Frames are stored as **differences** that a player integrates with a running sum in the stored width, so
a difference overshooting the signed range wraps exactly as that sum unwraps it. The first difference is
taken against zero, which makes it the waveform's first amplitude.

A loop reaching past the frames the file holds is drawn back inside them, and a waveform shorter than
the header states is read at the length the file holds; both are reported.

### Tuning

This format states a sample's pitch as a transposition. A sample sounds at the pitch of the key that
triggers it, shifted by `relative_note` whole semitones and trimmed by `finetune` in units of `1/128` of
a semitone. Under the linear frequency table the playback frequency for key `k` is

```
frequency = 8363 × 2 ** ((k + relative_note + finetune / 128 - 48) / 12)
```

Key 60 is C-5, the key at which a sample plays at exactly the rate the shared model records. Reading a
rate back inverts that expression, taking the remainder toward negative infinity so a whole-semitone
tuning leaves the trim at zero. The signed-byte relative note gives the format a reachable range of
`10 Hz` to `25662141 Hz`.

**The lattice is coarse, and it rounds.** `1/128` of a semitone is 0.78 cents, so a rate is stored to
within half of that: 0.39 cents, about 226 ppm. A sample recorded at 44100 Hz comes back as 44092 Hz —
inaudible as pitch, and real for a caller reconstructing a signal frame by frame.

## Later additions

The `header_size` field is this format's extension point, and later writers spend it: files state 27,
43, 57 and 81 there beside FastTracker 2's own 276, so seeking to `60 + header_size` is what reads them
all. Instrument headers state their own length the same way, and one shorter than the long form is read
as the short form. Version `0x0104` at offset 58 is what a reader expects.

## One instrument on its own (`.xi`)

One instrument makes a file of its own:

```
"Extended Instrument: "        21 bytes
instrument name                22 bytes
0x1A, tracker name, version    23 bytes, version 0x0102
keymap, envelopes, vibrato, fadeout    the body, to offset 296
sample count                   2 bytes, closing a 298-byte header
sample headers                 40 bytes each
sample frames                  differences, in header order
```

Behind its own identity block the file lays out **the same body a module's instrument header does**,
moved on by the 33 bytes the two identity blocks differ by. The sample count sits last here and third in
a module. The bounds are the format's own, so a sample staged below full gain is reported here exactly
as it is in a module: the field belongs to the format, whichever container a sample travels in.

## Timing

The header states a sixteen-bit speed at offset 76 and a sixteen-bit tempo at offset 78. Speed is the
ticks a row lasts and tempo the tick rate, so a row lasts `speed × 5 / (2 × tempo)` seconds, and at
44100 Hz and speed 1 the shortest whole-frame row this format reaches is 2 frames.

Real files carry a header speed of zero, which leaves a song no clock to advance on. It is read as this
format's own starting speed of 6, and reported.

## What this format carries

| Field | This format |
|---|---|
| Shared sample table | — each instrument owns its copies |
| Volume envelope | 12 points, `0..64` |
| Panning envelope | 12 points, `0..64` |
| Pitch envelope | — |
| Envelope sustain | one point |
| Envelope carry | — |
| Fadeout | `0..4095` canonical, counter 32768 |
| New note action | — |
| Sample volume | `0..64` |
| Sample gain | `64..64` |
| Sample panning | `0..255` |
| Sample auto-vibrato | type, sweep, depth, rate |
| Sample loop | forward, ping-pong |
| Sustain loop | — |
| Stereo waveforms | — |
| Compressed waveforms | — |
| Note column commands | key off |
| Song message | — |
| Song volume | — |
| Mix volume | — |
| Channel panning table | — |

| Content | Reported as |
|---|---|
| A note cut or fade in the note column | `ValueError` |
| A sustain loop | `ValueError` |
| A stereo waveform | `ValueError` |
| A pitch envelope | `ValueError` |
| An envelope sustaining across a span of points | `ValueError` |
| A keymap transposing one key of a sample differently from another | `ValueError` |
| A song whose cells name samples | `ValueError` |
| A volume-column intent this format leaves unnamed | `ValueError` |
| A quantity past a bound | `LimitError` |

See [`limits.md`](../limits.md) for the bounds, and [`conventions.md`](../conventions.md) for the rule
that separates the two.

## Effect commands

A command is a number printed as `0`–`9` and then `A` onwards, followed by one parameter byte.

| | | | |
|---|---|---|---|
| `0` arpeggio | `8` set panning | `G` global volume | `R` multi retrigger |
| `1` portamento up | `9` sample offset | `H` global volume slide | `T` tremor |
| `2` portamento down | `A` volume slide | `K` key off | `X` extra fine portamento |
| `3` tone portamento | `B` position jump | `L` set envelope position | |
| `4` vibrato | `C` set volume | `P` panning slide | |
| `5` tone portamento + volume slide | `D` pattern break | | |
| `6` vibrato + volume slide | `E` extended | | |
| `7` tremolo | `F` set speed or tempo | | |

`F` carries both clocks in one command, split by where the parameter falls: below `0x20` it sets the
ticks a row lasts, and at or above it the beats per minute. A mid-song tempo therefore tops out at 255
even in a module whose header carries more.

`D` reads its parameter a decimal digit to each nibble, so a break to row 16 is stored as `0x16`.

`E` selects a sub-command with its high nibble and passes it the low one:

| | | | |
|---|---|---|---|
| `1` fine portamento up | `5` finetune | `9` retrigger | `D` note delay |
| `2` fine portamento down | `6` pattern loop | `A` fine volume up | `E` pattern delay |
| `3` glissando | `7` tremolo waveform | `B` fine volume down | |
| `4` vibrato waveform | `8` panning | `C` note cut | |

See [`effects.md`](../effects.md) for the shared vocabulary these spell.

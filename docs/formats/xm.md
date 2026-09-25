# FastTracker 2 (`.xm`)

FastTracker 2 was written by Fredrik Huss and Magnus Högdahl of Triton and released in 1994 for MS-DOS. An
`.xm` file holds a song's patterns, order list and instruments. The instrument is the format's central unit: a
named voice that routes each of 96 keys onto one of its own samples, with envelopes and a fadeout of its own.

The sections sit one after another and are read front to back, and that choice shapes everything below.

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

The `header_size` field at offset 60 counts from that offset onward. It covers the rest of the header and the
whole order list, so a reader seeks to `60 + header_size` to find the first pattern. An instrument is
self-contained: its header, its sample headers, then its waveforms, in header order.

## Order list

The header holds `order_count` played positions at offset 64 and a `restart_position` at offset 66. The list
always takes its full 256 bytes, and each entry is one byte that names a pattern.

The parser moves a restart position past the last played entry back inside the list, drops an entry that names
a pattern missing from the file, and reports both.

## Patterns

A 9-byte pattern header holds its own length, a packing type, the row count and the packed byte count. Every
cell of every row is stored, and rows end by count, so a reader takes exactly `rows × channels` cells. **Each
cell is complete in itself**: a reader reads it on its own terms, and the grid is exactly what the stream
holds.

The first byte of a cell decides how it is read. **With the high bit set**, the byte is a mask, and only the
columns it names follow, in this order:

| Bit | Column |
|---|---|
| `0x01` | note |
| `0x02` | instrument |
| `0x04` | volume |
| `0x08` | effect command |
| `0x10` | effect parameter |

**With the high bit clear**, the byte *is* the note, and all five columns follow in full.

A cell with all five columns takes five bytes in the second form and six in the first, so a full cell leaves
out its mask. An empty cell takes one byte, its empty mask, so a silent pattern takes `rows × channels` bytes.
If the stream ends before the cells the header counts, the rest of the grid stays silent and is reported.

### The note column

Notes sit one **above** the shared numbering: key `k` is byte `k + 1`, byte `97` is a key off, and the eight
octaves this format numbers are shared keys `0..95`. Bytes 98 to 255 read as an absent note.

### The instrument column

The column names an **instrument**, one-based: byte `n` is instrument `n - 1`, and `0` leaves the channel on
the instrument it already plays. A cell that names an instrument past the end of the table reads the same way,
and is reported.

### The volume column

The byte holds a level as `0x10 + level` for levels `0..64`. The rest of its range holds ten effects, each in
a run of sixteen values:

| Run | Intent | Run | Intent |
|---|---|---|---|
| `0x60` | volume slide down | `0xB0` | vibrato depth |
| `0x70` | volume slide up | `0xC0` | panning |
| `0x80` | fine volume down | `0xD0` | panning slide left |
| `0x90` | fine volume up | `0xE0` | panning slide right |
| `0xA0` | vibrato speed | `0xF0` | portamento |

A cell that lists every column writes `0x00` where it has no volume, so that byte reads as an absent volume.
Two runs are left over: `0x01` to `0x0F` below the levels, and `0x51` to `0x5F` between the top level and the
first command. A byte from either run also reads as an absent volume, reported once for a whole pattern. See
[`volume.md`](../reference/volume.md).

## Instruments

The 263-byte instrument header holds its own length, a 22-byte name and a sample count, followed by a body: a
96-byte keymap that gives one sample position per key, two envelopes, an auto-vibrato and a fadeout. A key
that names a position past the samples the instrument stores is silent, and a silent key is written as the
first such position.

Each instrument holds **its own copies** of the samples its keys reach. A sample that two instruments both
play is therefore written twice and counted twice. Reading a module back gives one instrument per group of
samples, so a song whose two instruments shared one sample comes back holding two.

A stored sample has one transposition, so every key routed to it sounds the same pitch. A keymap that shifts
one key of a sample differently from another would need different values of that per-sample field, and is
refused.

An instrument that owns no samples is written in the **29-byte** short header, which ends after the sample
count. These 29 bytes are the opening of the long form, so a placeholder slot is cheap.

A key is what reaches a sample here, so a sample that an instrument counts but no key names is held in the
song's own table, and the parser reports how many. Writing that song back gives each instrument the samples
its keys play.

### Envelopes

The two envelopes, volume and panning, have at most 12 points each, with values `0..64`. Their point tables
sit at fixed offsets in the instrument header, volume from 129 and panning from 177, followed by the counts,
sustain points, loop bounds and flags. The flag bits are `0x01` enabled, `0x02` sustain, `0x04` loop.

The sustain is a **single point**, so an envelope that sustains across a span of points is refused. The parser
moves a loop or sustain outside the envelope's points back inside them, sets a point whose tick is out of
order to the tick before it, and reports both.

### Fadeout

A fading voice loses `fadeout` from a counter of **32768** every tick and falls silent after `32768 / fadeout`
ticks. The field is sixteen bits wide, and the tracker's own editor allows up to `0xFFF`: eight ticks, its
quickest fade.

The fade begins at the **key off**, wherever the volume envelope has reached, so a fade is set against the
curve of the volume envelope.

## Samples

The 40-byte sample header holds a length, a loop begin, a loop length, a volume, a finetune, a type byte, a
panning, a relative note and a 22-byte name. **Lengths count bytes**, so a 16-bit sample's stored length is
twice its frame count. The type byte holds the loop mode in its low two bits (`0` none, `1` forward, `2`
ping-pong) and the 16-bit flag at `0x10`.

Frames are stored as **differences**. A player adds them in a running sum at the stored width, so a difference
that overshoots the signed range wraps around, and the sum unwraps it exactly. The first difference is taken
against zero, so it equals the waveform's first amplitude.

The parser moves a loop that reaches past the frames in the file back inside them, reads a waveform shorter
than the header states at the length the file holds, and reports both.

### Tuning

This format stores a sample's pitch as a transposition. A sample sounds at the pitch of the key that triggers
it, shifted by `relative_note` whole semitones and trimmed by `finetune` in units of `1/128` of a semitone.
Under the linear frequency table, the playback frequency for key `k` is

```
frequency = 8363 × 2 ** ((k + relative_note + finetune / 128 - 48) / 12)
```

Key 60 is C-5, where a sample plays at exactly the rate the shared model records. Reading a rate back inverts
that expression. It takes the remainder toward negative infinity, so a whole-semitone tuning leaves the trim
at zero. The relative note is a signed byte, which gives a reachable range of `10 Hz` to `25662141 Hz`.

**The finetune steps are coarse, and rates round to them.** `1/128` of a semitone is 0.78 cents, so a rate is
stored to within half of that: 0.39 cents, about 226 ppm. A sample recorded at 44100 Hz comes back as 44092
Hz. That is inaudible as pitch, but it matters to a caller that reconstructs a signal frame by frame.

## Later additions

The `header_size` field is this format's extension point, and writers after FastTracker 2 use it in their own
ways. Seeking to `60 + header_size` therefore reads a module from any of them. An instrument header also holds
its own length. The record keeps this format's fields at their defined offsets at any stated length, and the
length says how far to step to the samples behind it. A reader expects version `0x0104` at offset 58.

The twenty bytes at offset 38 hold the name of the program that wrote the module. A file read here is written
back with the name it arrived with, and a song built from scratch is signed with this library's own name and
version. The field holds a genuine name, so a writer can sign its work there.

## One instrument on its own (`.xi`)

A single instrument can be stored as a file of its own:

```
"Extended Instrument: "        21 bytes
instrument name                22 bytes
0x1A, tracker name, version    23 bytes, version 0x0102
keymap, envelopes, vibrato, fadeout    the body, to offset 296
sample count                   2 bytes, closing a 298-byte header
sample headers                 40 bytes each
sample frames                  differences, in header order
```

After its own identity block, the file holds **the same body as a module's instrument header**, moved on by
the 33 bytes by which the two identity blocks differ. The sample count comes last here and third in a module.
The bounds belong to the format, so a sample staged below full gain is reported here exactly as in a module:
the field belongs to the format, whichever container a sample travels in.

## Timing

The header holds a sixteen-bit speed at offset 76 and a sixteen-bit tempo at offset 78. Speed is the number of
ticks in a row, and tempo is the tick rate. A row lasts `speed × 5 / (2 × tempo)` seconds. At 44100 Hz and
speed 1, the shortest whole-frame row this format reaches is 2 frames.

Real files hold a header speed of zero, which leaves a song no clock to advance on. The parser reads it as
this format's own starting speed of 6 and reports it.

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
| What names the writer | twenty bytes of header text |

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

See [`limits.md`](../reference/limits.md) for the bounds, and
[`architecture.md`](../contributing/architecture.md) for the rule that tells the two errors apart.

## Effect commands

A command is a number shown as `0`–`9` and then `A` onward, followed by one parameter byte.

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

`F` sets both clocks in one command, depending on the parameter: below `0x20` it sets the ticks a row lasts,
and at or above `0x20` the beats per minute. A mid-song tempo therefore tops out at 255, even in a module
whose header holds more.

`D` reads its parameter as one decimal digit per nibble, so a break to row 16 is stored as `0x16`.

`E` picks a sub-command with the high nibble (four bits) of its parameter and passes it the low one:

| | | | |
|---|---|---|---|
| `1` fine portamento up | `5` finetune | `9` retrigger | `D` note delay |
| `2` fine portamento down | `6` pattern loop | `A` fine volume up | `E` pattern delay |
| `3` glissando | `7` tremolo waveform | `B` fine volume down | |
| `4` vibrato waveform | `8` panning | `C` note cut | |

See [`effects.md`](../reference/effects.md) for the shared effect vocabulary that these commands express.

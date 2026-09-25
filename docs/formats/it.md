# Impulse Tracker (`.it`)

Impulse Tracker was written by Jeffrey Lim and released in 1995 for MS-DOS. An `.it` file holds a song's
patterns, order list and samples, and its instruments when the song plays that way. An instrument is a named
voice that routes each of 120 keys onto one of the song's samples, with three envelopes and a fadeout each.

The header locates every section through tables of offsets, and that choice shapes everything below.

## At a glance

| | |
|---|---|
| Tracker | Impulse Tracker, Jeffrey Lim, 1995 |
| Byte order | little-endian |
| A cell's instrument column names | a sample or an instrument, as one header bit says |
| Sections are found by | three tables of 32-bit offsets |
| Channels | 1..64 canonical, 1..127 extended and stored |
| Pattern rows | 32..200 canonical, 1..1024 extended, 1..65535 stored |
| Note range | 10 octaves, shared keys 0..119 |
| Waveform storage | 8- or 16-bit, signed or unsigned, absolute or differences, optionally compressed |
| One instrument on its own | `.iti` |

## File shape

```
IMPM file header                       192 bytes
order list                             one byte per position, then 0xFF
instrument, sample and pattern tables  4 bytes an entry, one entry per item
IMPI instrument headers                554 bytes each
IMPS sample headers                    80 bytes each
packed patterns                        8-byte header, then the cell stream
sample frames                          pointed at by each sample header
song message                           pointed at by the file header
```

The header holds the number of instruments, samples and patterns. Three tables of 32-bit offsets follow the
order list. A section can sit wherever its entry points, so the order above is this library's choice.

Each section starts with its own tag: `IMPM` opens the file, `IMPI` each instrument and `IMPS` each sample. A
table entry of zero points at no record. A pattern with that entry is stored nowhere and plays 64 empty rows.
An entry that points past the end of the file is read as an absent record too, and is reported.

Two 64-byte tables, at offsets 64 and 128, hold a panning and a volume for each of the format's 64 channels.
The header also holds the song's global volume, mix volume, panning separation and flag word.

**A module can attach free text.** The header holds the text's length at offset 54 and a 32-bit offset to it
at 56. Bit 0 of `special`, at offset 46, says whether a text block is attached. The text is terminated within
the length reserved for it, its lines are separated by `\r`, and the editor keeps up to 8000 bytes of it.

## Order list

The header holds the number of played positions at offset 32, and the list follows it directly. Each position
is one byte that names a pattern. `0xFF` ends the song and `0xFE` separates two stretches of it, so the reader
keeps the positions that play. A position that names a pattern missing from the file is dropped and reported.

## Patterns

An 8-byte pattern header holds the packed byte count and the row count, then a stream of channel markers.

Each row lists **only the channels that hold something** and ends with a `0x00` terminator. A silent channel
takes no bytes, and a completely silent pattern takes one byte a row. A listed channel starts with the byte
`channel + 1`, which has `0x80` set when a mask byte follows. The mask says what the cell holds:

| Bit | Meaning |
|---|---|
| `0x01` | a note byte follows |
| `0x02` | an instrument byte follows |
| `0x04` | a volume byte follows |
| `0x08` | a command and a parameter byte follow |
| `0x10` | reuse the channel's last note |
| `0x20` | reuse the channel's last instrument |
| `0x40` | reuse the channel's last volume |
| `0x80` | reuse the channel's last effect |

Every channel keeps a **memory** of the last note, instrument, volume and effect it used, and of its last
mask. A repeated column costs one bit. A marker with the high bit clear reuses the remembered mask, so a
steady channel takes a single byte a row. A channel's first marker with the high bit clear finds no mask, so
the cell holds no columns and reads as silence.

**The stream determines how wide a pattern is.** The format stores no channel count, so the width is the
highest channel that any row lists. A song with silent channels beyond its last used one would therefore come
back narrower. When the widest channel is silent in the grid, the writer announces it in the first row with an
empty mask, `0x80 | channels` then `0x00`, so the declared width survives a round trip.

Each of these reads as the silence a player sounds there, and is reported: a stream that stops inside a cell,
a marker that names no channel, and a header with no rows.

### The note column

Impulse Tracker numbers its keys from C-0, as the shared model does. A key is stored as its own number,
`0..119`. The top of the byte range holds commands: `253` fades a voice, `254` cuts it and `255` releases it.
The bytes in between read as an absent note, reported once for a whole pattern.

### The instrument column

The column is **one-based**: byte `n` names position `n - 1`, and `0` leaves the channel on whatever it
already plays. Bit 2 of the header's flag word says what a position means: an instrument when the bit is set,
a sample when it is clear. A file therefore uses one kind of address throughout.

A cell that names a position past the end of the table leaves the channel on what it already plays. A file
addressed by samples may still hold instrument definitions, which the parser sets aside as a tracker keeps
them for switching instruments back on. Both cases are reported.

### The volume column

A mask bit says whether the column is present, so an absent volume takes no byte:

| Bytes | Meaning | Amounts |
|---|---|---|
| `0..64` | a level | `0..64` |
| `65..74` / `75..84` | fine volume up / down | `0..9` |
| `85..94` / `95..104` | volume slide up / down | `0..9` |
| `105..114` / `115..124` | pitch slide down / up | `0..9` |
| `128..192` | panning | `0..64` |
| `193..202` | portamento | `0..9` |
| `203..212` | vibrato depth | `0..9` |

The bytes between these runs read as an absent volume, reported once for a whole pattern. See
[`volume.md`](../reference/volume.md).

## Instruments

A 554-byte instrument header holds a name, a DOS filename, a fadeout, a global volume, a default panning, the
new-note and duplicate behaviors, three envelopes and a keymap.

The keymap sits at offset 64 and holds 120 (sounded note, sample number) pairs, one per key. Sample numbers
are one-based, so zero silences a key, and an unmapped key sounds its own pitch. The pressed key and the
sounded note are separate, so one instrument routes keys to different samples and transposes each
independently.

Three repairs are reported. A key routed to a missing sample is silenced, a sounded note past the last key
moves back onto it, and a behavior byte with no defined meaning reads as that field's default.

### Envelopes

The three envelopes (volume, panning and pitch) sit at offsets `0x130`, `0x182` and `0x1D4`. Each starts with
six bytes (flags, point count, loop begin and end, sustain begin and end), followed by 25 nodes. A node is a
signed value byte and a little-endian tick word. The flags are `0x01` enabled, `0x02` loop, `0x04` sustain,
`0x08` carry and `0x80` filter, which makes the pitch envelope a filter cutoff.

The value byte is signed and holds `-128..127`. Impulse Tracker uses `0..64` of it for volume and `-32..32`
for panning and pitch. **The sustain is a span**, so the curve can hold across two points. **Carry** lets a
new note keep the envelope's position: an envelope with carry on resumes where the previous note left it.

The parser moves a loop or sustain span that lies outside the envelope's points back inside them, sets a point
whose tick is out of order to the tick before it, and reports both.

### Fadeout

A fading voice loses `fadeout` from a counter of **1024** every tick and falls silent after `1024 / fadeout`
ticks. The field is sixteen bits wide, and the editor allows up to 128: eight ticks, its quickest fade.

The fade begins where the volume envelope **ends**. The longer the envelope runs, the later the fade starts.
See [`README.md`](README.md) for where the formats disagree about a shared field.

## Samples

An 80-byte sample header holds a name, a DOS filename, a global volume, a default volume, a flag byte, a
convert byte, a panning, a length, two loop ranges, a rate, a pointer to the frames and four auto-vibrato
bytes. **The length counts frames** per channel, at any bit depth.

The flag byte combines storage and looping: `0x01` the header has stored frames, `0x02` sixteen-bit, `0x04`
stereo, `0x08` compressed, `0x10` loop, `0x20` sustain loop, `0x40` ping-pong loop and `0x80` ping-pong
sustain. Both loops can therefore run back and forth.

The panning byte holds a position in `0..64`, its high bit an enable switch. The global volume is a per-sample
multiplier on the playing level. Three repairs are reported: a loop past the stored frames moves inside them,
a file ending inside a waveform gives the frames it holds, and a rate of zero reads as 8363 Hz.

**The convert byte says how to read the frames.** Its low bit tells signed amplitudes, which Impulse Tracker
itself writes, from unsigned ones, which sit one full scale higher and are common in files converted from
Scream Tracker 3. Its third bit marks the frames as differences that a player sums. Any other bit names
storage this reader cannot decode, such as big-endian frames, ADPCM or a synthesizer's own waveform. Such a
sample reads as signed amplitudes and is reported.

**Waveforms can be compressed**, as nearly every module from a modern tracker is. Each block starts with the
byte count that follows it and holds at most `0x8000` frames of an eight-bit waveform or `0x4000` of a
sixteen-bit one. A block's values are bit fields whose width travels in the stream beside them. They are
differences, summed in a running sum that restarts with each block. Version 2.15 sums twice, and the convert
byte says which. Fields that run out read as silence and are reported.

**Waveforms can be stereo.** The `0x04` flag marks two channels of frames, and the length counts frames per
channel. Impulse Tracker's own editor writes mono. OpenMPT, Schism Tracker and other later players store the
channels **planar**: the whole left channel then the whole right, or two independent compressed streams. Both
channels share every other header field.

### Tuning

The rate is stored as **C5Speed**: the frequency in hertz at which the sample sounds when key C-5 is pressed.
The shared model records the same value, so a 44100 Hz recording comes back at 44100 Hz. The editor counted up
to 9999999 hertz, but the 32-bit field holds far more, so the two ceilings differ.

## Later additions

Later trackers use the room past the records the header points at. Three kinds of block reach the model:

- **An editing history** sits directly after the offset tables. No pointer leads to it, so a reader learns
  that it exists only from bit 1 of the header's `special` field.
- **Channel and pattern names** follow it. Each block has a four-byte tag, a length, and one fixed-width field
  per name: twenty bytes for a channel and thirty-two for a pattern. The reader walks the blocks by their
  lengths, so it skips over a tag that this library does not interpret.
- **Anything a writer appended** closes the file, after the last record that any header points at. The reader
  finds it where the format's own content ends. OpenMPT keeps its extended properties there.

These blocks sit between the offset tables and the records, so they shift every offset that the header holds.

Offset 40 holds the version of the program that wrote the module, in twelve bits with a program number of its
own above them. Several programs also sign a mark in four bytes at offset 60. Both are kept as they arrive.
Offset 42 holds the version a file was written for and stays `0x0214`, because the instrument record written
here includes the filter bytes at 58 and 59 that Impulse Tracker 2.14 added.

| Number | Program | Mark | Program |
|---|---|---|---|
| `0x0` | Impulse Tracker | `OMPT` | OpenMPT |
| `0x1` | Schism Tracker | `CHBI` | ChibiTracker |
| `0x5` | OpenMPT | `TMOD` | this library |

## One instrument on its own (`.iti`)

A single instrument can be stored as a file of its own:

```
IMPI instrument header            554 bytes
IMPS sample headers               80 bytes each
sample frames                     pointed at by each sample header
```

The instrument header's sample count says how many sample headers follow it. A reader finds each one by
arithmetic, where a module uses an offset table. Each sample pointer still counts from the start of the file,
so one reader serves both containers. The keymap refers to the samples in the order they are stored.

## Timing

The header holds a one-byte speed at offset 50 and a one-byte tempo at offset 51. Speed is the number of ticks
in a row, and tempo is the tick rate. A row lasts `speed × 5 / (2 × tempo)` seconds. At 44100 Hz and speed 1,
the shortest whole-frame row this format reaches is 441 frames, because the one-byte tempo limits it there.

## What this format carries

| Field | This format |
|---|---|
| Shared sample table | one table, addressed by every instrument |
| Volume envelope | 25 points, `0..64` |
| Panning envelope | 25 points, `-32..32` |
| Pitch envelope | 25 points, `-32..32`, or a filter cutoff |
| Envelope sustain | a span of points |
| Envelope carry | resumes where the previous note left it |
| Fadeout | `0..128` canonical, counter 1024 |
| New note action | cut, continue, note off, note fade |
| Sample volume | `0..64` |
| Sample gain | `0..64` |
| Sample panning | `0..64`, behind an enable bit |
| Sample auto-vibrato | speed, depth, rate, waveform |
| Sample loop | forward, ping-pong |
| Sustain loop | forward, ping-pong |
| Stereo waveforms | two planar channels |
| Compressed waveforms | blocks, summed once or twice |
| Note column commands | off, cut, fade |
| Song message | `0..8000` canonical, `\r` separated |
| Song volume | `0..128` canonical, one byte stored |
| Mix volume | `0..128` canonical, one byte stored |
| Channel panning table | 64 entries, beside a 64-entry channel volume table |
| What names the writer | a program number above a version, and a signature in four reserved bytes |

| Content | Reported as |
|---|---|
| A volume-column intent this format leaves unnamed | `ValueError` |
| A quantity past a bound | `LimitError` |

This table has two rows to FastTracker 2's nine; [`limits.md`](../reference/limits.md) lists the bounds.

## Effect commands

A command is a number shown as a letter, `A` through `Z`, followed by one parameter byte.

| | | | |
|---|---|---|---|
| `A` set speed | `H` vibrato | `O` sample offset | `V` global volume |
| `B` position jump | `I` tremor | `P` panning slide | `W` global volume slide |
| `C` pattern break | `J` arpeggio | `Q` retrigger | `X` set panning |
| `D` volume slide | `K` vibrato + volume slide | `R` tremolo | `Y` panbrello |
| `E` portamento down | `L` portamento + volume slide | `S` extended | `Z` MIDI macro |
| `F` portamento up | `M` channel volume | `T` set tempo | |
| `G` tone portamento | `N` channel volume slide | `U` fine vibrato | |

Speed and tempo are separate commands, `A` and `T`. `C` breaks to the row it names as a plain number.

`S` picks a sub-command with the high nibble (four bits) of its parameter and passes it the low one:

| | | | |
|---|---|---|---|
| `1` glissando | `5` panbrello waveform | `9` sound control | `D` note delay |
| `2` finetune | `6` pattern delay in ticks | `A` high offset | `E` pattern delay in rows |
| `3` vibrato waveform | `7` note control | `B` pattern loop | `F` MIDI macro select |
| `4` tremolo waveform | `8` panning | `C` note cut | |

See [`effects.md`](../reference/effects.md) for the shared effect vocabulary that these commands express.

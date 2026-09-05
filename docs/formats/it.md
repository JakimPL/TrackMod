# Impulse Tracker (`.it`)

Impulse Tracker was written by Jeffrey Lim and released in 1995 for MS-DOS. An `.it` file holds a song's
patterns, its order list, its samples, and — when the song plays that way — its instruments: named voices
that route each of 120 keys onto one of the song's samples, with three envelopes and a fadeout each.

The header points at everything through offset tables, and that decision shapes everything below.

## At a glance

| | |
|---|---|
| Tracker | Impulse Tracker, Jeffrey Lim, 1995 |
| Byte order | little-endian |
| A cell's instrument column names | a sample or an instrument, as one header bit states |
| Sections are found by | three tables of 32-bit offsets |
| Channels | 1..64 canonical, 1..127 stored |
| Pattern rows | 32..200 canonical, 1..200 stored |
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

The header counts the instruments, samples and patterns the file holds, and three tables of 32-bit
offsets follow the order list, one entry per item. A section sits wherever its entry points, so the order
above is one this library chose, with the frames a sample header points at last.

Each section carries its own tag: `IMPM` opens the file, `IMPI` each instrument, `IMPS` each sample. An
entry of zero points at no record, which is how a pattern stored nowhere is stated; it plays 64 empty rows.

Two 64-byte tables, at offsets 64 and 128, hold a panning and a volume for each of the format's own 64
channels, beside the song's global volume, mix volume, panning separation and flag word.

**A module may attach free text.** The header states its length at offset 54, points at it with a 32-bit
offset at 56, and sets bit 0 of `special` at 46 to say a block is attached at all. The text is terminated
inside the length reserved for it, its lines separated by `\r`; the editor keeps 8000 bytes of it.

## Order list

The header counts played positions at offset 32, and the list follows it immediately, one byte per
position naming a pattern. `0xFF` ends the song and `0xFE` separates two stretches of it, so a reader
keeps the positions that play. A position naming a pattern the file leaves out is dropped, and reported.

## Patterns

An 8-byte pattern header states the packed byte count and the row count, and what follows is a stream of
channel markers — where this format spends its cleverness.

Each row lists **only the channels carrying something** and ends with a `0x00` terminator, so a silent
channel costs nothing at all and a pattern of pure silence is one byte a row. A listed channel is
announced by the byte `channel + 1`, with `0x80` set when a mask byte follows:

| Bit | The cell states |
|---|---|
| `0x01` | a note byte follows |
| `0x02` | an instrument byte follows |
| `0x04` | a volume byte follows |
| `0x08` | a command and a parameter byte follow |
| `0x10` | the note this channel last stated |
| `0x20` | the instrument it last stated |
| `0x40` | the volume it last stated |
| `0x80` | the effect it last stated |

Every channel keeps a **memory** of the four values it last stated and of the mask it last used. A repeated
column costs one bit, and a marker leaving the high bit clear carries the mask that channel last used, so a
channel holding steady settles to a single byte a row. A channel whose first marker sets no mask starts
from one over no columns, which reads as the silence already in the grid.

**How wide a pattern is comes out of the stream.** The format states a channel count nowhere, so the width
is the widest channel any row lists, and a song holding channels in reserve would come back narrower. The
writer closes that gap: where the grid leaves the widest channel silent, the opening row announces it with
a mask over no columns — `0x80 | channels` then `0x00` — so the declared width survives a round trip.

### The note column

Impulse Tracker numbers its keyboard from C-0 exactly as the shared model does, so a key is stored as its
own number in `0..119`. The commands sit at the top of the byte: `253` fades a voice, `254` cuts it, `255`
releases it. The bytes between read as an absent note, reported once for a whole pattern.

### The instrument column

The column is **one-based**: byte `n` names position `n - 1`, and `0` leaves the channel on what it
already carries. What that position numbers is what bit 2 of the header's flag word says — an instrument
when it is set, a sample when it is clear — so one file addresses one way throughout.

A cell naming a position past the table the file holds carries its channel on, and a sample-addressed
file's instrument definitions are set aside for the switch going back on; both are reported.

### The volume column

A mask bit says whether the column is present at all, so every byte in it means something:

| Bytes | States | Amounts |
|---|---|---|
| `0..64` | a level | `0..64` |
| `65..74` / `75..84` | fine volume up / down | `0..9` |
| `85..94` / `95..104` | volume slide up / down | `0..9` |
| `105..114` / `115..124` | pitch slide down / up | `0..9` |
| `128..192` | panning | `0..64` |
| `193..202` | portamento | `0..9` |
| `203..212` | vibrato depth | `0..9` |

The bytes between the runs read as an absent volume, reported once for a whole pattern. See
[`volume.md`](../volume.md).

## Instruments

A 554-byte instrument header carries a name, a DOS filename, a fadeout, a global volume, a default
panning, the new-note and duplicate behaviours, three envelopes and a keymap.

The keymap is 120 pairs of (sounded note, sample number) at offset 64, one per key. Sample numbers are
one-based, so zero silences a key, and an unmapped key names its own pitch. Separating the pressed key from
the sounded note lets one instrument route keys onto different samples and transpose each independently.

Instruments sit beside the sample table and index into it, so a shared waveform is stored once and named twice.

A key routed to a missing sample is left silent, a sounded note past the last key is drawn onto it, and a
behaviour byte this format leaves unnamed reads as that field's default. All three are reported.

### Envelopes

Three envelopes — volume, panning and pitch — sit at offsets `0x130`, `0x182` and `0x1D4`. Each opens with
six bytes — flags, point count, loop begin and end, sustain begin and end — then 25 nodes of a signed value
byte and a little-endian tick word. The flags are `0x01` enabled, `0x02` loop, `0x04` sustain, `0x08` carry
and `0x80` filter, which reads the pitch envelope as a filter cutoff instead.

Impulse Tracker reads `0..64` of the value byte for volume and `-32..32` for panning and pitch. **The
sustain is a span**, so a curve may hold across two points, and **carry** is what a new note keeps: an
envelope carrying on resumes where the previous note left it.

A loop or sustain span stated outside its own points is drawn back inside them, and points stated out of
order are held at the tick before them; both are reported.

### Fadeout

A fading voice loses `fadeout` from a counter of **1024** every tick, so it falls silent after
`1024 / fadeout` ticks. The field is sixteen bits wide, and the editor counts to 128 — eight ticks, the
quickest fade it states.

The fade begins where the volume envelope **ends**, so an instrument whose curve runs on fades that much
later. See [`README.md`](README.md) for where the four formats disagree about a shared field.

## Samples

An 80-byte sample header states a name, a DOS filename, a global volume, a default volume, a flag byte, a
convert byte, a panning, a length, two loop ranges, a rate, a pointer to the frames, and four auto-vibrato
bytes. **The length counts frames**, per channel, whatever the depth.

The flag byte carries storage and looping together: `0x01` frames are stored at all, `0x02` sixteen-bit,
`0x04` stereo, `0x08` compressed, `0x10` loop, `0x20` sustain loop, `0x40` ping-pong loop, `0x80`
ping-pong sustain — so both loops are optionally bidirectional.

The panning byte reserves its high bit as an enable switch and holds a position on `0..64`, and the global
volume is a per-sample multiplier applied on top of whatever level plays. A loop past the frames stored is
drawn inside them and a rate of zero reads as 8363 Hz; both are reported.

**The convert byte says how the frames are read.** Its low bit distinguishes signed amplitudes, which
Impulse Tracker itself writes, from unsigned ones, which sit a full scale higher and are common in files
converted from Scream Tracker 3. Its third bit marks the frames as differences a player sums. Any other bit
names storage this reader has no rendering for — big-endian frames, ADPCM, a synthesiser's own waveform —
and reads as signed amplitudes, reported.

**Waveforms may be compressed**, which is what nearly every module a modern tracker writes carries. Each
block opens with the byte count that follows it and holds at most `0x8000` frames of an eight-bit waveform
or `0x4000` of a sixteen-bit one. Inside a block the values are bit fields whose width travels in the
stream beside them, and what they carry are the differences of a running sum that restarts with each block.
Version 2.15 sums twice, and the convert byte says which; fields that run out read as silence, reported.

**Waveforms may be stereo.** The `0x04` flag says a sample's frames are two channels, and the length counts
frames per channel either way. Impulse Tracker's own editor writes mono; OpenMPT, Schism Tracker and other
later players store the channels **planar** — the whole left channel then the whole right, or two
independent compressed streams. Every other field the header states is one both channels share.

### Tuning

The rate is stored as **C5Speed**: the hertz at which the sample sounds when key C-5 is pressed. That is
what the shared model records, written straight out, so a 44100 Hz recording comes back at 44100 Hz, and
the 32-bit field counts to 9999999.

## Later additions

Impulse Tracker left the file room past the records its own header points at, and the trackers that came
after it spend that room. Three kinds of block reach the model:

- **An editing history** sits directly after the offset tables. Nothing points at it, so bit 1 of the
  header's `special` field is the whole of how a reader knows it is there.
- **Channel and pattern names** follow it, each a four-byte tag, the length that follows, and one
  fixed-width field per name — twenty bytes for a channel, thirty-two for a pattern. The blocks are walked
  by their own lengths, so a tag this library has no reading for is stepped over.
- **Whatever a writer appended** past the last record any header points at closes the file, found by where
  this format's own content stops. OpenMPT keeps its extended properties there.

The stated blocks sit between the offset tables and the records, so they move every offset the header states.

The header carries at offset 40 the version of whatever program wrote the module, each taking a number of
its own above the twelve version bits: `0x0` Impulse Tracker, `0x1` Schism Tracker, `0x5` OpenMPT. A file
read here and written back states the origin it arrived with.

## One instrument on its own (`.iti`)

One instrument makes a file of its own:

```
IMPI instrument header            554 bytes
IMPS sample headers               80 bytes each
sample frames                     pointed at by each sample header
```

The header's sample count says how many headers follow it, so a reader finds each by arithmetic where a
module consults an offset table. Each sample pointer is still counted from the start of the file, which
lets one reader serve both containers. The keymap's one-based numbers name the samples stored here, in the
order they are stored.

## Timing

The header states a one-byte speed at offset 50 and a one-byte tempo at 51. Speed is the ticks a row lasts
and tempo the tick rate, so a row lasts `speed × 5 / (2 × tempo)` seconds, and at 44100 Hz and speed 1 the
shortest whole-frame row this format reaches is 441 frames — the one-byte tempo is what holds it there.

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
| Sample panning | `0..255` |
| Sample auto-vibrato | speed, depth, rate, waveform |
| Sample loop | forward, ping-pong |
| Sustain loop | forward, ping-pong |
| Stereo waveforms | two planar channels |
| Compressed waveforms | blocks, read at either sum |
| Note column commands | off, cut, fade |
| Song message | `0..8000` canonical, `\r` separated |
| Song volume | `0..128` |
| Mix volume | `0..128` |
| Channel panning table | 64 entries, beside a 64-entry channel volume table |

| Content | Reported as |
|---|---|
| A volume-column intent this format leaves unnamed | `ValueError` |
| A quantity past a bound | `LimitError` |

Its refusals are two rows where FastTracker 2's are nine; [`limits.md`](../limits.md) states the bounds.

## Effect commands

A command is a number printed as `A` through `Z`, followed by one parameter byte.

| | | | |
|---|---|---|---|
| `A` set speed | `H` vibrato | `O` sample offset | `V` global volume |
| `B` position jump | `I` tremor | `P` panning slide | `W` global volume slide |
| `C` pattern break | `J` arpeggio | `Q` retrigger | `X` set panning |
| `D` volume slide | `K` vibrato + volume slide | `R` tremolo | `Y` panbrello |
| `E` portamento down | `L` portamento + volume slide | `S` extended | `Z` MIDI macro |
| `F` portamento up | `M` channel volume | `T` set tempo | |
| `G` tone portamento | `N` channel volume slide | `U` fine vibrato | |

Speed and tempo are separate commands here, `A` and `T`, and `C` breaks to the plain row it names.

`S` selects a sub-command with its high nibble and passes it the low one:

| | | | |
|---|---|---|---|
| `1` glissando | `5` panbrello waveform | `9` sound control | `D` note delay |
| `2` finetune | `6` pattern delay in ticks | `A` high offset | `E` pattern delay in rows |
| `3` vibrato waveform | `7` note control | `B` pattern loop | `F` MIDI macro select |
| `4` tremolo waveform | `8` panning | `C` note cut | |

See [`effects.md`](../effects.md) for the shared vocabulary these spell.

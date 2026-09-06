# Scream Tracker 3 (`.s3m`)

Scream Tracker 3 was written by Sami Tammilehto of Future Crew and released in 1994 for MS-DOS. An `.s3m`
file holds a song's patterns, its order list and its sounds — one table of eighty-byte records that is
the instrument table and the sample table at once, since a record here is a waveform and what plays it.

Every section is found through a table of paragraph numbers, and that decision shapes everything below.

## At a glance

| | |
|---|---|
| Tracker | Scream Tracker 3, Sami Tammilehto, 1994 |
| Byte order | little-endian |
| A cell's instrument column names | a sample |
| Sections are found by | two tables of 16-bit entries, each naming a 16-byte paragraph |
| Channels | 1..16 canonical, 1..32 extended and stored |
| Pattern rows | 64 |
| Note range | 8 octaves, shared keys 12..107 canonical, 12..119 stored |
| Waveform storage | 8- or 16-bit, unsigned or signed, one channel or two |
| One instrument on its own | — |

## File shape

```
SCRM file header               96 bytes, its tag at offset 44
order list                     one byte per position
sample pointer table           2 bytes an entry, one per record
pattern pointer table          2 bytes an entry, one per pattern
channel panning table          32 bytes
SCRS sample records            80 bytes each
packed patterns                a 2-byte block length, then the cell stream
sample frames                  pointed at by each record
```

Every block a table names opens on a **paragraph** of sixteen bytes, so a two-byte entry reaches
1048560 bytes into the file and whatever came before a block is padded out to its boundary. A record
points at its own frames with a third byte on top of that pair, reaching 268435440 — which is why the
waveforms take the ground the file runs furthest over and the records and the patterns come first.

Those two distances are what bound a module's size, and a song packing more than either of them reaches
is reported as `block_offset` or `sample_offset` rather than met as an overflow.

The header counts the positions, the records and the patterns at offsets 32, 34 and 36, carries a word of
song-wide switches at 38, the program that wrote the module at 40 and the sign of its frames at 42, and
states `SCRM` at 44. The global volume, the speed, the tempo and the mixing byte follow at 48 through 51,
and the mixing byte spends its seven low bits on the level and the one above them on stereo playback.

**A module states its width in a table.** Thirty-two bytes from offset 64 give each channel a mixer slot —
`0` to `7` on the left, `8` to `15` on the right, the numbers above them the synthesiser's own channels,
`0x80` added to mute a slot and `0xFF` for a channel this module leaves out. A cell names its channel by
the slot it takes here, so the last slot the table names is how wide every pattern reads.

Scream Tracker 3 lays a song's channels down one to each side in turn, so a module opens spread across
the field: `0`, `8`, `1`, `9`, and on.

**Where each channel opens is a block of its own.** The thirty-two bytes after the pointer tables hold a
position per channel, and the byte at 53 says they are there to read by holding `0xFC` exactly, which is
the one value a reader takes for the block being present. Each entry reserves a bit for stating a
position at all and holds it in the low nibble, sixteen steps across the field, so a channel claiming
none opens on the side its own mixer slot puts it.

## Order list

The header counts the played positions at offset 32, and the list follows the header immediately, one
byte to a position naming a pattern. `0xFE` marks a position to step over and `0xFF` ends the song.

A file holding further positions past an end carries a section a player sounds as a piece of its own, and
every one of them is music the table names, so the order list keeps them all. A position naming a pattern
the file leaves out is dropped, and reported.

## Patterns

A pattern is 64 rows, always. Its block opens with the length of the whole block and continues as a
stream of channel markers, and each row lists **only the channels carrying something** and ends with a
`0x00` terminator. A silent channel therefore costs nothing at all and a pattern of pure silence is one
byte a row — the cheapest silence of the formats here.

A marker holds the channel in its five low bits and says which groups of bytes follow it:

| Bit | The cell states |
|---|---|
| `0x20` | a note byte and a sample byte follow |
| `0x40` | a volume byte follows |
| `0x80` | a command and a parameter byte follow |

Nothing is remembered between cells, so what a pattern costs is a count of the groups its columns fill.
The trackers of this lineage disagree over whether the two length bytes are counted in the length they
state, so the stated length is read as the room the stream has and the row terminators as where it ends —
which reads a block counted either way to the same music.

A stream ending before the sixty-fourth row leaves the rows it never reached silent, a stream stopping
inside a cell leaves that cell silent as well, a cell on a channel past the width the settings state is
left out, and a pointer past the bytes the file holds names an absent pattern; all four are reported. A
pointer of **zero** is how this format stores a pattern of sixty-four empty rows, so it plays them and is
read without a word.

### The note column

The byte spells a key as an **octave over a semitone**, a nibble each, and counts its octaves from the one
above the model's own: the key a byte names is `12 × octave + semitone + 12`. The deepest key this format
reaches is therefore the model's C-1, so how deep the music reaches is graded as much as how high, and a
cell asking for a key below that octave is refused by name.

`254` cuts a voice and `255` states nothing. A semitone nibble naming more than the twelve in an octave
reads as an absent note, and so does an octave nibble of `9` or above, whose key would climb past the ten
octaves the model numbers. Both are reported once for a whole pattern.

### The instrument column

The column is **one-based**: byte `n` names record `n - 1`, and `0` leaves the channel on the sample it
already plays. The note and the sample share one marker bit, so a cell stating either of them writes both
bytes and fills the one it leaves alone with the value that names nothing.

A cell naming a record past the table the file holds carries its channel on, and it is reported.

### The volume column

A marker bit says whether the column is present at all, and the byte spends its range on two things:

| Bytes | States | Amounts |
|---|---|---|
| `0..64` | a level | `0..64` |
| `128..192` | panning | `0..64` |

The bytes between and above the two runs read as an absent volume, reported once for a whole pattern.
Panning here is as fine as Impulse Tracker's and four times finer than the sixteen steps this format's own
channel table holds. See [`volume.md`](../volume.md).

## Samples

An 80-byte `SCRS` record states what it holds in the byte it opens with: `0` an empty slot, `1` a
waveform, and `2` through `7` an OPL patch. **The length counts frames**, per channel, whatever the depth.

```
 0  what the record holds        28  volume
 1  12-byte DOS filename         29  one reserved byte
13  the frames' paragraph, high  30  packing byte
14  the same, low word           31  storage and looping flags
16  length in frames, 4 bytes    32  C2Spd, 4 bytes
20  loop begin, 4 bytes          36  twelve reserved bytes
24  loop end, 4 bytes            48  28-byte name
                                 76  the tag `SCRS`
```

Two runs of the record carry no field a reader here reads — one byte after the volume and twelve after
the rate — and a writer leaves both as zeroes.

The flag byte carries storage and looping together: `0x01` a forward loop, `0x02` stereo, `0x04`
sixteen-bit. **Frames sit in the positive half of their range**, shifted a full scale up from where they
sound, and the header states at offset 42 which half a module uses — Scream Tracker 3 wrote signed frames
in its first release and unsigned ones ever after, so a reader follows the header. A stereo waveform
holds each channel in full, the left before the right.

An empty slot keeps the name, the filename, the rate, the level and the width a tracker held ready for
the waveform to come, so a module written again states what it stated, and a pointer past the bytes the
file holds names a slot just as empty. A loop past the frames stored is drawn inside them, a loop whose
ends meet repeats nothing and plays through once, a waveform the file stops inside reads as the frames it
holds, and a rate of zero reads as 8363 Hz; all are reported.

**A record may describe an OPL patch where a sampled one points at frames.** Scream Tracker 3 played six
kinds of them — a melodic voice and five drums — and spends the eighty bytes on the synthesiser's
registers. Such a record is refused by name. Sounding one means a patch held beside the sample table,
where a waveform sits inside it, which is the shape the model leaves room for.

### Tuning

The rate is stored as **C2Spd**: the hertz at which the sample sounds when the key the note byte `0x40`
names is pressed, which is the shared model's key 60. That is what the model records, written straight
out, so a 44100 Hz recording comes back at 44100 Hz. The field is 32 bits wide and Scream Tracker 3 reads
the low word of it, so a rate past 65535 is stored faithfully and graded.

## Later additions

Scream Tracker 3 wrote eight-bit mono waveforms and one packing, and the trackers that came after it
spend the room its record left. Three things reach a reader:

- **Stereo and sixteen-bit frames** are two flag bits the trackers after it set, and both are read here.
- **A packing byte** states the ADPCM a later tracker wrote, which is refused by name.
- **The word at offset 40** states the program and the version that wrote the module, `0x1320` being
  Scream Tracker 3.20 itself. A file read here and written back states the origin it arrived with.

The word at offset 38 carries eight switches, most of them naming an older tracker's reading. The highest
says a writer attached a block of its own, which the word at offset 62 points at.

| Bit | Asks for | Bit | Asks for |
|---|---|---|---|
| `0x01` | Scream Tracker 2's vibrato | `0x10` | Amiga period limits |
| `0x02` | Scream Tracker 2's tempo | `0x20` | the filter |
| `0x04` | Amiga slides | `0x40` | Scream Tracker 3's own volume slides |
| `0x08` | the zero-volume optimisation | `0x80` | a block of the writer's own |

## Timing

The header states a one-byte speed at offset 49 and a one-byte tempo at 50. Speed is the ticks a row lasts
and tempo the tick rate, so a row lasts `speed × 5 / (2 × tempo)` seconds, and at 44100 Hz and speed 1 the
shortest whole-frame row this format reaches is 441 frames — the same floor Impulse Tracker's one-byte
tempo holds it to.

A tempo below 32 is read as this format's own starting tempo of 125, and a speed below 1 as its starting
speed of 6; both are reported. Every player of this lineage draws a slower tempo up to 32, which is what
puts the floor there.

## What this format carries

| Field | This format |
|---|---|
| Shared sample table | one table of records, addressed by every cell |
| Volume envelope | — |
| Panning envelope | — |
| Pitch envelope | — |
| Envelope sustain | — |
| Envelope carry | — |
| Fadeout | — |
| New note action | — |
| Sample volume | `0..64` |
| Sample gain | `64..64` |
| Sample panning | — |
| Sample auto-vibrato | — |
| Sample loop | forward |
| Sustain loop | — |
| Stereo waveforms | two planar channels |
| Compressed waveforms | — |
| Note column commands | cut |
| Song message | — |
| Song volume | `0..64` canonical, one byte stored |
| Mix volume | `0..127` |
| Channel panning table | 32 entries, sixteen positions each |

| Content | Reported as |
|---|---|
| A note off or a note fade in the note column | `ValueError` |
| A per-sample panning | `ValueError` |
| A sustain loop | `ValueError` |
| A loop that plays backwards | `ValueError` |
| A volume-column intent this format leaves unnamed | `ValueError` |
| A song whose cells name instruments | `ValueError` |
| A record describing an OPL patch | `ValueError` |
| A waveform stored in ADPCM | `ValueError` |
| A quantity past a bound | `LimitError` |

The OPL patch and the packed waveform are met while reading, where every other refusal here is met while
writing. [`limits.md`](../limits.md) states the bounds behind the closing row.

## Effect commands

A command is a number printed as `A` through `X`, followed by one parameter byte.

| | | | |
|---|---|---|---|
| `A` set speed | `G` tone portamento | `O` sample offset | `T` set tempo |
| `B` position jump | `H` vibrato | `Q` retrigger | `U` fine vibrato |
| `C` pattern break | `I` tremor | `R` tremolo | `V` global volume |
| `D` volume slide | `J` arpeggio | `S` extended | `X` set panning |
| `E` portamento down | `K` vibrato + volume slide | | |
| `F` portamento up | `L` portamento + volume slide | | |

The letters run with gaps in them, and Impulse Tracker numbered its own commands over this set and filled
those gaps. Speed and tempo are separate commands here, `A` and `T`, which is the arrangement Impulse
Tracker inherited. `C` reads its parameter a decimal digit to each nibble, so a break to row 16 is stored
as `0x16`, and `X` counts the stereo field in 129 steps — the finer of the two grids this format states a
position on.

`S` selects a sub-command with its high nibble and passes it the low one:

| | | | |
|---|---|---|---|
| `0` filter | `3` vibrato waveform | `A` stereo control | `D` note delay |
| `1` glissando | `4` tremolo waveform | `B` pattern loop | `E` pattern delay |
| `2` finetune | `8` panning | `C` note cut | `F` funk repeat |

See [`effects.md`](../effects.md) for the shared vocabulary these spell.

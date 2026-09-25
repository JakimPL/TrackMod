# Scream Tracker 3 (`.s3m`)

Sami Tammilehto of Future Crew wrote Scream Tracker 3 and released it in 1994 for MS-DOS. An `.s3m` file
holds a song's patterns, its order list and its sounds. The sounds sit in one table of eighty-byte records.
That table is the instrument table and the sample table at once, because each record is a waveform together
with the settings that play it.

The file finds every section through a table of paragraph numbers. That design shapes everything below.

## At a glance

| | |
|---|---|
| Tracker | Scream Tracker 3, Sami Tammilehto, 1994 |
| Byte order | little-endian |
| A cell's instrument column names | a sample |
| Sections are found by | two tables of 16-bit entries, each pointing to a 16-byte paragraph |
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

Every block that a table points to starts on a **paragraph**, a 16-byte boundary, and padding fills the
space before each block up to that boundary. A two-byte entry therefore reaches 1048560 bytes into the file.
A record points to its own frames with a third byte added to that pair, which reaches 268435440. That is why
the waveforms come last, where the file reaches furthest, and the records and the patterns come before them.

These distances bound a module's size. A song beyond either is reported as `block_offset` or `sample_offset`.

The header gives the counts of positions, records and patterns at offsets 32, 34 and 36. It holds a word of
song-wide switches at 38, the program that wrote the module at 40, the frame sign (signed or unsigned) at
42, and the tag `SCRM` at 44. The global volume, the speed, the tempo and the mixing byte follow at 48
through 51. The mixing byte uses its seven low bits for the level and the bit above them for stereo
playback.

**A table gives the module's width.** Thirty-two bytes from offset 64 assign each channel a mixer slot.
Slots `0` to `7` play on the left and `8` to `15` on the right. Higher numbers are the synthesizer's own
channels. Adding `0x80` mutes a slot, and `0xFF` marks a channel this module leaves out. A cell names its
channel by its slot in this table, so the last slot the table names sets how wide every pattern reads.

Scream Tracker 3 alternates a song's channels between the two sides, so a module opens spread across the
stereo field: `0`, `8`, `1`, `9`, and so on.

**A separate block gives each channel's starting position.** The thirty-two bytes after the pointer tables
hold one entry per channel. The block is present when the byte at offset 53 holds exactly `0xFC`, and any
other value means it is absent. Each entry has a bit that says whether it states a position at all. The
position sits in the low nibble, in sixteen steps across the field. A channel that states none starts on
the side its own mixer slot puts it.

## Order list

The header counts the played positions at offset 32. The list follows the header directly, with one byte
per position naming a pattern. `0xFE` marks a position to skip and `0xFF` ends the song.

Some files hold further positions after an end marker. A player sounds such a section as a piece of its own.
Every position in it is music the table names, so the order list keeps them all. A position that names a
pattern the file leaves out is dropped and reported.

## Patterns

A pattern is always 64 rows. Its block opens with the length of the whole block and continues as a stream of
channel markers. Each row lists **only the channels that hold something** and ends with a `0x00`
terminator. A silent channel costs no bytes, so a pattern of pure silence takes one byte per row. That is
the cheapest silence among the formats here.

A marker holds the channel in its five low bits and says which groups of bytes follow it:

| Bit | The cell states |
|---|---|
| `0x20` | a note byte and a sample byte follow |
| `0x40` | a volume byte follows |
| `0x80` | a command and a parameter byte follow |

No cell depends on the one before it, so the size of a pattern is the number of byte groups its columns
fill. Trackers of this lineage disagree on whether the stated length includes the two length bytes. The
reader therefore takes the stated length as the room the stream has, and the row terminators as the place
where it ends. Both ways of counting then give the same music.

The parser reports four cases:

- A stream ends before the sixty-fourth row, and the rows it never reached read as silent.
- A stream stops inside a cell, and that cell reads as silent.
- A cell sits on a channel past the width the settings state, and the parser leaves it out.
- A pointer points past the bytes the file holds, and it names an absent pattern.

A pointer of **zero** stores a pattern of sixty-four empty rows. The parser plays them and reports nothing.

### The note column

The byte spells a key as an **octave** and a **semitone**, one nibble each. Its octave count starts one
octave above the model's own, so the byte names the key `12 × octave + semitone + 12`. The lowest key this
format reaches is therefore the model's C-1, so a song's lowest keys are graded as well as its highest. A
cell that asks for a key below that octave is refused.

`254` cuts a voice and `255` states nothing. A semitone nibble of 12 or more reads as an absent note. So
does an octave nibble of `9` or above, because its key would climb past the ten octaves the model numbers.
Both are reported once for a whole pattern.

### The instrument column

The column is **one-based**: byte `n` points to record `n - 1`, and `0` leaves the channel on the sample it
already plays. The note and the sample share one marker bit. A cell that states either one therefore writes
both bytes and fills the other with the value that names nothing.

A cell that points to a record past the table the file holds carries its channel on. The parser reports it.

### The volume column

A marker bit says whether the cell has a volume byte at all. The byte's range covers two things:

| Bytes | States | Amounts |
|---|---|---|
| `0..64` | a level | `0..64` |
| `128..192` | panning | `0..64` |

Bytes between the two runs and bytes above them read as an absent volume, reported once for a whole
pattern. Panning here is as fine as Impulse Tracker's, and four times finer than the sixteen steps that
this format's own channel table holds. See [`volume.md`](../reference/volume.md).

## Samples

An 80-byte `SCRS` record starts with a byte that says what it holds: `0` an empty slot, `1` a waveform,
and `2` through `7` an OPL patch. **The length counts frames**, per channel, whatever the depth.

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

Two runs of the record hold no field a reader here reads: one byte after the volume and twelve after the
rate. A writer leaves both as zeroes.

The flag byte holds the storage and looping settings together: `0x01` a forward loop, `0x02` stereo, `0x04`
sixteen-bit. **Frames are usually unsigned**, so they sit in the positive half of their range, shifted a full
scale up from where they sound. The header says at offset 42 whether a module uses signed or unsigned frames.
Scream Tracker 3 wrote signed frames in its first release and unsigned ones ever after, so a reader follows
the header. A stereo waveform holds each channel in full, the left before the right.

An empty slot keeps the name, the filename, the rate, the level and the width that a tracker held ready for
the waveform to come, so a module written again states what it stated. A pointer past the bytes the file
holds names a slot that is just as empty. The parser also repairs and reports four cases:

- A loop past the stored frames moves back inside them.
- A loop whose ends meet repeats nothing, so the sample plays through once.
- A waveform where the file ends reads as the frames the file holds.
- A rate of zero reads as 8363 Hz.

**A record can describe an OPL patch where a sampled one points to frames.** Scream Tracker 3 played six
kinds of patch, a melodic voice and five drums, and used the eighty bytes for the synthesizer's registers.
The parser refuses such a record. Playing one would need a patch held beside the sample table, while the
model holds a waveform inside the table.

### Tuning

The rate is stored as **C2Spd**: the frequency in hertz at which the sample sounds when the player presses
the key that the note byte `0x40` names. That is the shared model's key 60. The model records the rate as
this frequency, so the writer stores it directly, and a 44100 Hz recording comes back at 44100 Hz. The field
is 32 bits wide and Scream Tracker 3 reads the low word of it, so a rate past 65535 is stored exactly and
graded.

## Later additions

Scream Tracker 3 wrote eight-bit mono waveforms with one packing, and the trackers that came after it use
the room its record left. Four things reach a reader:

- **Stereo and sixteen-bit frames** are two flag bits that the later trackers set. This library reads both.
- **A packing byte** marks the ADPCM that a later tracker wrote. The parser refuses it.
- **The word at offset 40** holds the program and the version that wrote the module: `0x1320` is Scream
  Tracker 3.20 itself, `0x2` Imago Orpheus, `0x3` Impulse Tracker, `0x4` Schism Tracker and `0x5` OpenMPT.
  Each number belongs to the program that claimed it, so a file keeps the one it arrived with and a file
  written here holds `0x1320`.
- **The eight bytes at offset 54** hold a mark that a tracker can sign in place of that number. Sound Club
  writes `SCLUB2.0` there, and this library writes `TrackMod`. A mark names the writer, while the number
  names the reading. A file keeps the mark it arrived with.

The word at offset 38 holds eight switches, and most of them select an older tracker's behavior. The
highest switch says the writer attached a block of its own, and the word at offset 62 points to it.

| Bit | Asks for | Bit | Asks for |
|---|---|---|---|
| `0x01` | Scream Tracker 2's vibrato | `0x10` | Amiga period limits |
| `0x02` | Scream Tracker 2's tempo | `0x20` | the filter |
| `0x04` | Amiga slides | `0x40` | Scream Tracker 3's own volume slides |
| `0x08` | the zero-volume optimization | `0x80` | a block of the writer's own |

## Timing

The header holds a one-byte speed at offset 49 and a one-byte tempo at offset 50. Speed is the number of
ticks a row lasts, and tempo is the tick rate. A row lasts `speed × 5 / (2 × tempo)` seconds. At 44100 Hz
and speed 1, the shortest whole-frame row this format reaches is 441 frames, the same floor that Impulse
Tracker's one-byte tempo sets.

The parser reads a tempo below 32 as this format's starting tempo of 125, and a speed below 1 as its
starting speed of 6. It reports both. Every player of this lineage raises a slower tempo to 32, which is
why the floor sits there.

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
| What names the writer | a program number above a version, and a signature in eight reserved bytes |

| Content | Reported as |
|---|---|
| A note off or a note fade in the note column | `ValueError` |
| A per-sample panning | `ValueError` |
| A sustain loop | `ValueError` |
| A loop that plays backward | `ValueError` |
| A volume-column intent this format leaves unnamed | `ValueError` |
| A song whose cells name instruments | `ValueError` |
| A record describing an OPL patch | `ValueError` |
| A waveform stored in ADPCM | `ValueError` |
| A record that opens with a type this format does not define | `ValueError` |
| A header that opens with anything but this format's tag | `ValueError` |
| A quantity past a bound | `LimitError` |

The four rows before the closing row are met while reading, and every other refusal here is met while
writing. [`limits.md`](../reference/limits.md) lists the bounds behind the closing row.

## Effect commands

A command is a number, printed as a letter from `A` through `X`, followed by one parameter byte.

| | | | |
|---|---|---|---|
| `A` set speed | `G` tone portamento | `O` sample offset | `T` set tempo |
| `B` position jump | `H` vibrato | `Q` retrigger | `U` fine vibrato |
| `C` pattern break | `I` tremor | `R` tremolo | `V` global volume |
| `D` volume slide | `J` arpeggio | `S` extended | `X` set panning |
| `E` portamento down | `K` vibrato + volume slide | | |
| `F` portamento up | `L` portamento + volume slide | | |

The letters have gaps. Impulse Tracker numbered its own commands over this set and filled the gaps. Speed
and tempo are separate commands here, `A` and `T`, the arrangement Impulse Tracker inherited. `C` reads its
parameter as one decimal digit per nibble, so a break to row 16 is stored as `0x16`. `X` counts the stereo
field in 129 steps, the finer of the two grids this format uses for a position.

`S` selects a sub-command with its high nibble and passes it the low nibble:

| | | | |
|---|---|---|---|
| `0` filter | `3` vibrato waveform | `A` stereo control | `D` note delay |
| `1` glissando | `4` tremolo waveform | `B` pattern loop | `E` pattern delay |
| `2` finetune | `8` panning | `C` note cut | `F` funk repeat |

See [`effects.md`](../reference/effects.md) for the shared vocabulary these commands express.

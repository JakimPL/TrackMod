# Amiga ProTracker (`.mod`)

The Amiga Freelancers released Amiga ProTracker in 1990. It was the last in a line of trackers that began
with Karsten Obarski's Ultimate Soundtracker in 1987. A `.mod` file holds a song's patterns, its order list
and thirty-one sampled sounds, and that is the whole file. A cell names one of the samples, and the key it
plays at is the pitch it sounds.

The header has a fixed size of 1084 bytes. That design shapes everything below.

## At a glance

| | |
|---|---|
| Tracker | Amiga ProTracker, Amiga Freelancers, 1990 |
| Byte order | big-endian |
| A cell's instrument column names | a sample |
| Sections are found by | walking fixed sizes, front to back |
| Channels | 4 canonical, 1..32 extended, 1..99 stored |
| Pattern rows | 64 |
| Note range | 3 tabulated octaves, shared keys 48..83 canonical, 21..119 stored |
| Waveform storage | 8-bit signed, one channel |
| One instrument on its own | — |

## File shape

```
module name                    20 bytes
sample records                 30 bytes each, thirty-one of them
order count and restart        2 bytes
order table                    128 bytes
format tag                     4 bytes, closing a 1084-byte header
patterns                       64 rows of four-byte cells, at the width the tag states
sample frames                  in record order, at the length each record states
```

Every offset here is arithmetic. A section begins where the sizes of the sections before it put it. A reader
finds a pattern by multiplying its three dimensions and finds the waveforms by adding up all the patterns.
The four tag bytes give the channel count, so a reader reads them first.

**A file's pattern count has two sources.** The order table names the highest pattern a song plays. The
space between the header and the waveforms holds every pattern that was stored. A module can store patterns
that its order never reaches, and then it stores more than the table names. The reader takes the larger of
the two counts, which keeps every pattern and puts the waveforms at the right offset.

## Order list

The header holds the number of positions that play in one byte at offset 950, and a restart position in the
next byte. The table always takes its full 128 bytes, with one byte per position naming a pattern.

The parser moves a count above the table's 128 positions back to 128, drops a position that names a pattern
the file leaves out, and reports both. Trackers of this lineage often write a marker into the restart byte
instead of a position, most often the full width of the table. The byte therefore lives in two places. A
file's own byte is kept in this format's settings and written back unchanged. A song built from scratch
writes the restart position its order list holds.

## Patterns

A pattern is 64 rows of one four-byte cell per channel. The file writes every cell, whether or not it holds
anything. The stream opens directly with the cells and runs to the end of the grid, so a pattern costs
`rows × channels × 4` bytes whatever it holds, and a reader locates it by arithmetic.

Each cell spreads its four columns across its four bytes:

| Byte | Bits | The cell states |
|---|---|---|
| 0 | `0xF0` | the sample number's high nibble |
| 0 | `0x0F` | the period's four high bits |
| 1 | all | the period's eight low bits |
| 2 | `0xF0` | the sample number's low nibble |
| 2 | `0x0F` | the effect command |
| 3 | all | the effect parameter |

The sample number is split around the twelve bits that the period fills. That split is what makes a cell
exactly four bytes with no mask anywhere. If the cells end before the grid does, the rest of the grid is
silent, as a player would sound it, and the parser reports it.

### The note column

The column holds an **Amiga period**, the divider that the sound chip uses to count out a sample. It holds
the pitch only. ProTracker tabulates three octaves of periods, from 856 down to 113. Every tracker that
reached past those octaves scaled the table by octaves, which is exact because an octave doubles the
period. The twelve bits a cell has for the period limit the reach to shared keys 21 to 119.

Each tracker wrote its own table, and the tables differ in the last digit. The parser therefore reads a
period as the key it comes closest to, and reports once per pattern how many periods it moved to a key. A
period more than half a semitone from every key lies outside the octaves this format tabulates, and it
reads as an absent note.

### The instrument column

The column is **one-based**. The two nibbles join into a sample number, where `n` points to position
`n - 1` and `0` leaves the channel on the sample it already plays. A cell that names a sample past the
table the file holds carries its channel on, and the parser reports it.

## Samples

A 30-byte sample record holds a 22-byte name, a length, a finetune, a volume and one loop. **Every length
counts pairs of frames**, so a record gives half the byte count of its waveform. Waveforms are eight-bit
and one channel throughout. A module always writes all thirty-one records, whether a song fills them or
leaves them empty, so one more sample costs its frames only.

A loop length of one pair means the sample plays through once, so a real loop is two pairs or longer. When
the writer stores a loop, it moves the beginning back to the pair that holds it and the end on to the pair
that closes it. Every frame the loop repeats then sits inside the region the record names. A waveform of a
single pair has no room for a loop. The parser moves a loop that reaches past the frames the file holds
back inside them, holds a volume above full at full, and reports both.

Trackers of this lineage wrote liner notes into the sample names, so a slot with no waveform can still hold
text that the file means to keep. A song therefore holds every slot up to the last one that holds anything:
a waveform, a name, or a cell that names it.

### Tuning

A record stores its tuning as a **finetune**: one of sixteen rows of periods, an eighth of a semitone
apart. The row sets the rate at which a sample plays its own key. The value is a **signed nibble**. `0` is
the untrimmed 8363 Hz, and `1` through `7` sharpen the rate up to 8795 Hz. `8` through `15` are the
negative rows, running from 7893 Hz up to 8305 Hz.

These sixteen rates are all this format can express, so a sample recorded at any other rate is graded
against them. The grade asks the caller to resample it onto a row.

## Later additions

Four bytes at offset 1080 hold a **tag**. The tag is all a reader has to go on, because the format holds
no version number, and two files of the same length hold different music depending on their tags.
ProTracker's own tag is `M.K.`. It was joined by `M!K!` once a song held more than the sixty-four patterns
that the plain tag was first read with.

Every tracker that widened the format past four channels wrote a tag of its own, so the reader knows the
width before it reads any pattern byte:

| Tag | Channels | Written by |
|---|---|---|
| `M.K.`, `M!K!`, `LARD`, `NSMS` | 4 | Amiga ProTracker |
| `M&K!` | 4 | His Master's Noise |
| `N.T.`, `.M.K` | 4 | NoiseTracker |
| `FLT4` | 4 | StarTrekker |
| `CD61`, `CD81` | 6, 8 | Octalyser |
| `FA04`, `FA06`, `FA08` | 4, 6, 8 | Digital Tracker |
| `TDZ1` through `TDZ4` | 1..4 | TakeTracker |
| `1CHN` through `9CHN`, `10CH` through `99CH` | 1..99 | the multichannel families |

A tag for a layout that stores its patterns another way is refused. `FLT8` is one: it writes each
eight-channel pattern as two four-channel ones. The fifteen-sample layout from before any tag existed has
no tag at all. It is read as [Soundtracker](st.md), whose header is shorter by half a sample table.

## Timing

The clock lives in the cells. Every module starts at six ticks a row and 125 beats per minute, the start
every tracker of this lineage uses. A song switches to another clock by setting it where the music needs
it. A row lasts `speed × 5 / (2 × tempo)` seconds, so at 44100 Hz and speed 1 the shortest whole-frame row
this format reaches is 441 frames.

This format's capacities fix the starting values at 6 and 125. A song that asks to start anywhere else
receives a report, so the clock it asked for stays visible. A mid-song change can reach the effect's own
range, which is one parameter byte.

## What this format carries

| Field | This format |
|---|---|
| Shared sample table | one table of thirty-one slots, addressed by every cell |
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
| Stereo waveforms | — |
| Compressed waveforms | — |
| Note column commands | — |
| Song message | — |
| Song volume | — |
| Mix volume | — |
| Channel panning table | — |
| What names the writer | the tag, naming the family that settled the layout |

| Content | Reported as |
|---|---|
| A volume in a cell | `ValueError` |
| A note command of any kind | `ValueError` |
| A stereo waveform | `ValueError` |
| A sixteen-bit waveform | `ValueError` |
| A per-sample panning | `ValueError` |
| A sustain loop | `ValueError` |
| A loop that plays backward | `ValueError` |
| A loop over a waveform of one pair of frames | `ValueError` |
| An effect command past the four bits a cell holds | `ValueError` |
| A song whose cells name instruments | `ValueError` |
| A tag naming a layout that stores its patterns another way | `ValueError` |
| A tag naming none of the dialects this format reads | `ValueError` |
| A quantity past a bound | `LimitError` |

The two tag rows are met while reading, and every other refusal here is met while writing. This table has
thirteen rows against Impulse Tracker's two, because this is the plainest of the formats here. Each field
it fills is also filled by the other four formats, with two exceptions. FastTracker 2 keeps its samples per
instrument instead of in one table, and the older Amiga layout leaves its writer unnamed.
[`limits.md`](../reference/limits.md) lists the bounds behind the last row.

## Effect commands

A command is one nibble, shown as `0`–`9` and then `A` onward, followed by one parameter byte.

| | | | |
|---|---|---|---|
| `0` arpeggio | `4` vibrato | `8` set panning | `C` set volume |
| `1` portamento up | `5` tone portamento + volume slide | `9` sample offset | `D` pattern break |
| `2` portamento down | `6` vibrato + volume slide | `A` volume slide | `E` extended |
| `3` tone portamento | `7` tremolo | `B` position jump | `F` set speed or tempo |

The command field is four bits, so the set has sixteen commands. Every later tracker widened the set. The
ones descended from this format keep these sixteen at the same numbers.

`F` sets both clocks in one command, and the parameter value decides which: below `0x20` it sets the ticks
a row lasts, and from `0x20` up it sets the beats per minute. FastTracker 2 inherited this arrangement
unchanged. `D` reads its parameter as one decimal digit per nibble, so a break to row 16 is stored as
`0x16`.

`E` selects a sub-command with its high nibble and passes it the low nibble:

| | | | |
|---|---|---|---|
| `0` filter | `4` vibrato waveform | `9` retrigger | `D` note delay |
| `1` fine portamento up | `5` finetune | `A` fine volume up | `E` pattern delay |
| `2` fine portamento down | `6` pattern loop | `B` fine volume down | `F` invert loop |
| `3` glissando | `7` tremolo waveform | `C` note cut | |

`E8` is left out of the table. The trackers that wrote this format put different things there, so a cell
that carries it keeps its bytes as they are, for whoever knows which tracker wrote them.

See [`effects.md`](../reference/effects.md) for the shared vocabulary these commands express.

# Amiga ProTracker (`.mod`)

Amiga ProTracker was released in 1990 by the Amiga Freelancers, the last in a line of trackers that began
with Karsten Obarski's Ultimate Soundtracker in 1987. A `.mod` file holds a song's patterns, its order
list and thirty-one sampled sounds, and that is the whole of it: a cell names one of the samples, and the
key it is played at is the pitch it sounds.

The header is a fixed slab of 1084 bytes, and that decision shapes everything below.

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

Every offset here is arithmetic: a section begins where the sizes of the ones before it put it, so a
reader reaches a pattern by multiplying its three dimensions and reaches the waveforms by adding up all
the patterns. The four tag bytes are what state the width, and they are read first.

**How many patterns a file holds has two answers.** The order table names the highest one a song plays,
and the room left between the header and the waveforms holds however many were stored, so a module
carrying patterns its order never reaches stores more than it names. Taking the larger of the two keeps
both, and reading the waveforms at the right offset depends on it.

## Order list

The header states how many positions play in one byte at offset 950, and a restart position in the next.
The table occupies its full 128 bytes whatever the count, one byte to a position naming a pattern.

A count past the 128 the table holds is drawn back to it, and a position naming a pattern the file leaves
out is dropped; both are reported. Trackers of this lineage write a marker into the restart byte — most
often the full width of the table — so the byte a file stated is kept and written back as it stood.

## Patterns

A pattern is 64 rows of one four-byte cell per channel, every one of them written whether it states
anything or not. The cells are the whole of it — the stream opens straight into them and runs to the end
of the grid — so a pattern costs `rows × channels × 4` bytes whatever it holds, and a reader takes it by
arithmetic.

Each cell spreads its four columns across its four bytes:

| Byte | Bits | The cell states |
|---|---|---|
| 0 | `0xF0` | the sample number's high nibble |
| 0 | `0x0F` | the period's four high bits |
| 1 | all | the period's eight low bits |
| 2 | `0xF0` | the sample number's low nibble |
| 2 | `0x0F` | the effect command |
| 3 | all | the effect parameter |

The sample number is split around the twelve bits the period fills, which is what makes a cell exactly
four bytes with no mask anywhere. A run of cells ending before the grid does leaves the rest of the grid
silent, which is what a player sounds there, and it is reported.

### The note column

The column holds an **Amiga period**: the divider the sound chip counts a sample out at, so the column
states a pitch and nothing else. ProTracker tabulates three octaves of them, 856 down to 113, and every
tracker that reached past those scaled the table by octaves — which is exact, an octave being a doubling
of the period. The twelve bits a cell leaves for it are what bound the reach, at shared keys 21 to 119.

Each tracker wrote its own table and they disagree in the last digit, so a period is read as the key it
comes closest to, and a pattern reports once how many it drew. A period further than half a semitone
from every key states a pitch outside the octaves this format tabulates, and reads as an absent note.

### The instrument column

The column is **one-based**: the two nibbles join into a sample number, `n` naming position `n - 1`, and
`0` leaves the channel on the sample it already plays. A cell naming a sample past the table the file
holds carries its channel on, and it is reported.

## Samples

A 30-byte sample record states a 22-byte name, a length, a finetune, a volume and one loop. **Every
length counts pairs of frames**, so a record states half the byte count of a waveform, which is
eight-bit and one channel throughout. A module writes all thirty-one records whether a song fills them
or leaves them empty, which is what makes one more sample cost its frames and nothing else.

A loop length of one pair is what this format writes to say a sample plays through once, so a loop runs
from two pairs up. Writing one takes its beginning back to the pair holding it and its end on to the pair
closing it, which keeps every frame it repeats inside the region the record names; a waveform of a single
pair leaves a loop no room at all. A loop reaching past the frames the file holds is drawn inside them and
a volume past full is drawn back to it; both are reported.

Trackers of this lineage wrote liner notes into the sample names, so a slot holding no waveform still
carries text a file means to keep. A song therefore holds every slot up to the last one that states
anything at all — a waveform, a name, or a cell naming it.

### Tuning

A record states its tuning as a **finetune**: one of sixteen rows of periods an eighth of a semitone
apart, and the row is what says the rate a sample plays its own key at. The rows run from 7893 Hz through
the untrimmed 8363 Hz to 8795 Hz, and the sixteen of them are the whole reach this format has — so a
sample recorded anywhere else is graded against that lattice, which asks a caller to resample it onto a
row.

## Later additions

Four bytes at offset 1080 carry a **tag**, and it is the whole of what a reader has: this format states a
version nowhere, and two files of the same length hold different music depending on the tag they carry.
ProTracker's own is `M.K.`, joined by `M!K!` once a song holds more patterns than the plain tag was first
read with.

Every tracker that widened the format past four channels wrote a tag of its own, so the width is settled
before a single pattern byte is read:

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

A tag naming a layout that stores its patterns another way is refused by name — `FLT8` writes each
eight-channel pattern as two four-channel ones — and so is the fifteen-sample layout written before any
tag existed, which reaches the same refusal by carrying no tag at all.

## Timing

The clock lives in the cells. A module starts on the one every tracker of this lineage starts on — six
ticks a row at 125 beats per minute — and a song reaches another by setting it where the music asks for
it. A row lasts `speed × 5 / (2 × tempo)` seconds, so at 44100 Hz and speed 1 the shortest whole-frame row
this format reaches is 441 frames.

The header holds those two values at 6 and 125, so a song asking to start anywhere else is told so, which
keeps the clock it asked for visible. What a mid-song change may reach is the effect's own range, which is
one parameter byte.

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

| Content | Reported as |
|---|---|
| A volume in a cell | `ValueError` |
| A note command of any kind | `ValueError` |
| A stereo waveform | `ValueError` |
| A sixteen-bit waveform | `ValueError` |
| A per-sample panning | `ValueError` |
| A sustain loop | `ValueError` |
| A loop that plays backwards | `ValueError` |
| A loop over a waveform of one pair of frames | `ValueError` |
| An effect command past the four bits a cell holds | `ValueError` |
| A song whose cells name instruments | `ValueError` |
| A quantity past a bound | `LimitError` |

Eleven rows against Impulse Tracker's two: this is the plainest of the formats here, and what it carries
every other one carries too. [`limits.md`](../limits.md) states the bounds behind the last of them.

## Effect commands

A command is one nibble printed as `0`–`9` and then `A` onwards, followed by one parameter byte.

| | | | |
|---|---|---|---|
| `0` arpeggio | `4` vibrato | `8` set panning | `C` set volume |
| `1` portamento up | `5` tone portamento + volume slide | `9` sample offset | `D` pattern break |
| `2` portamento down | `6` vibrato + volume slide | `A` volume slide | `E` extended |
| `3` tone portamento | `7` tremolo | `B` position jump | `F` set speed or tempo |

Sixteen commands is the whole set, because the field is four bits. Every tracker that came after this one
widened it, and the ones descended from it kept these sixteen at the numbers they hold here.

`F` carries both clocks in one command, split by where the parameter falls: below `0x20` it sets the
ticks a row lasts, and at or above it the beats per minute. FastTracker 2 inherited the arrangement whole.
`D` reads its parameter a decimal digit to each nibble, so a break to row 16 is stored as `0x16`.

`E` selects a sub-command with its high nibble and passes it the low one:

| | | | |
|---|---|---|---|
| `0` filter | `4` vibrato waveform | `9` retrigger | `D` note delay |
| `1` fine portamento up | `5` finetune | `A` fine volume up | `E` pattern delay |
| `2` fine portamento down | `6` pattern loop | `B` fine volume down | `F` invert loop |
| `3` glissando | `7` tremolo waveform | `C` note cut | |

`E8` is left out: the trackers that wrote this format put different things there, so a cell carrying it
keeps the bytes it holds for whoever knows which tracker wrote them.

See [`effects.md`](../effects.md) for the shared vocabulary these spell.

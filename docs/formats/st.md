# Soundtracker (`.mod`)

Karsten Obarski's Ultimate Soundtracker, published in 1987 for the Amiga, is where this whole family
begins: the first program to store a song's patterns, its order list and its sampled sounds in one file.
Several trackers wrote the same layout after it, and Amiga ProTracker grew out of them three years later.
A file holds fifteen sampled sounds, and a cell names one of them: the key it is played at is the pitch
it sounds.

The header is a fixed slab of 600 bytes, and that decision shapes everything below.

## At a glance

| | |
|---|---|
| Tracker | Ultimate Soundtracker, Karsten Obarski, 1987 |
| Byte order | big-endian |
| A cell's instrument column names | a sample |
| Sections are found by | walking fixed sizes, front to back |
| Channels | 4 |
| Pattern rows | 64 |
| Note range | 3 tabulated octaves, shared keys 48..83 canonical, 21..119 stored |
| Waveform storage | 8-bit signed, one channel |
| One instrument on its own | — |

## File shape

```
module name                    20 bytes
sample records                 30 bytes each, fifteen of them
order count and tempo          2 bytes
order table                    128 bytes, closing a 600-byte header
patterns                       64 rows of four channels of four-byte cells
sample frames                  in record order, at the length each record states
```

Every offset here is arithmetic: a section begins where the sizes of the ones before it put it, and the
width is settled before a byte is read, because every module of this format plays the four channels the
machine had. A reader reaches a pattern by multiplying its three dimensions and reaches the waveforms by
adding up all the patterns.

**A file states nothing about which format it is.** There is no tag and no magic here — both arrived with
the trackers that came after. What names the layout is the arithmetic itself: the fifteen records state
how much waveform the file ends with, the order table names the last pattern before it, and a file of
this format is exactly as long as the two come to behind its header. A file carrying a tag states which
tracker wrote it, and is read as [that format](mod.md) instead.

**How many patterns a file holds has two answers.** The order table names the highest one a song plays,
and the room left between the header and the waveforms holds however many were stored. Taking the larger
of the two keeps both, and reading the waveforms at the right offset depends on it.

## Order list

The header states how many positions play in one byte at offset 470, and the table occupies its full 128
bytes whatever the count, one byte to a position naming a pattern. A song plays from its first position
through to the count, and starts again at the beginning.

A count past the 128 the table holds is drawn back to it, and a position naming a pattern the file leaves
out is dropped; both are reported.

## Patterns

A pattern is 64 rows of one four-byte cell per channel, every one of them written whether it states
anything or not. The cells are the whole of it — the stream opens straight into them and runs to the end
of the grid — so a pattern costs 1024 bytes whatever it holds, and a reader takes it by arithmetic.

Each cell spreads its four columns across its four bytes:

| Byte | Bits | The cell states |
|---|---|---|
| 0 | `0xF0` | the sample number's high nibble |
| 0 | `0x0F` | the period's four high bits |
| 1 | all | the period's eight low bits |
| 2 | `0xF0` | the sample number's low nibble |
| 2 | `0x0F` | the effect command |
| 3 | all | the effect parameter |

Fifteen samples reach the low nibble alone, and the high one is what Amiga ProTracker spent on the
sixteen slots it added. A run of cells ending before the grid does leaves the rest of the grid silent,
which is what a player sounds there, and it is reported.

### The note column

The column holds an **Amiga period**: the divider the sound chip counts a sample out at, so the column
states a pitch and nothing else. Three octaves are tabulated, 856 down to 113, and those thirty-six keys
are the whole of what this format's own trackers wrote. The twelve bits a cell leaves for the field reach
further, at shared keys 21 to 119, so a file stating a scaled period is read at the key it names.

Each tracker of this family wrote its own table and they disagree in the last digit, so a period is read
as the key it comes closest to, and a pattern reports once how many it drew. A period further than half a
semitone from every key states a pitch outside the octaves tabulated, and reads as an absent note.

### The instrument column

The column is **one-based**: the two nibbles join into a sample number, `n` naming position `n - 1`, and
`0` leaves the channel on the sample it already plays. A cell naming a sample past the fifteen the file
holds carries its channel on, and it is reported.

## Samples

A 30-byte sample record states a 22-byte name, a length, a finetune, a volume and one loop — the same
record Amiga ProTracker kept. **The length counts pairs of frames**, so a record states half the byte
count of a waveform, which is eight-bit and one channel throughout. A module writes all fifteen records
whether a song fills them or leaves them empty, which is what makes one more sample cost its frames and
nothing else.

**A loop begins at a byte here**, where the trackers after this one counted the same field in pairs, and
its length counts pairs in both. A loop length of one pair says a sample plays through once, so a loop
runs from two pairs up, and writing one takes its end on to the pair closing it, which keeps every frame
it repeats inside the region the record names.

A loop reaching past the frames the file holds is drawn inside them, and a volume past full is drawn back
to it; both are reported.

The trackers of this format shipped a sample library and wrote the name a waveform came from into the
record, so a slot holding no waveform still carries text a file means to keep. A song therefore holds
every slot up to the last one that states anything at all — a waveform, a name, or a cell naming it.

### Tuning

The finetune byte is written zero, and every sample plays its own key at the untrimmed 8363 Hz. Amiga
ProTracker is where the field grew its sixteen rows of periods an eighth of a semitone apart, and the
byte is read on that lattice here, so a file stating one keeps what it stated and a rate recorded off the
lattice is graded against it.

## Later additions

The trackers that followed Ultimate Soundtracker wrote this same layout and spent the effect nibble
further, which is where `B`, `C`, `D` and `F` below arrive. They state nothing about themselves, so a
file gives no way to tell which of them wrote it, and a cell holding a command none of them numbered
keeps the bytes it carries for whoever knows.

The byte after the order count is where these trackers wrote a speed of their own, in units each read
its own way. A file's byte is kept in this format's settings and written back as it stood, and a song
built from nothing states the 120 every module of this format opens on.

## Timing

The clock is the machine's. A module runs at the one every tracker of this family runs at — six ticks a
row at 125 beats per minute — and a row lasts `speed × 5 / (2 × tempo)` seconds, so at 44100 Hz and speed
1 the shortest whole-frame row this format reaches is 441 frames.

This format's capacities pin those two values at 6 and 125, so a song asking to start anywhere else is
told so, which keeps the clock it asked for visible. What a mid-song `F` may reach is the five bits a
player reads it in.

## What this format carries

| Field | This format |
|---|---|
| Shared sample table | one table of fifteen slots, addressed by every cell |
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
| A song resuming past its first position | `ValueError` |
| A stereo waveform | `ValueError` |
| A sixteen-bit waveform | `ValueError` |
| A per-sample panning | `ValueError` |
| A sustain loop | `ValueError` |
| A loop that plays backwards | `ValueError` |
| A loop over a waveform of one pair of frames | `ValueError` |
| An effect command past the four bits a cell holds | `ValueError` |
| A song whose cells name instruments | `ValueError` |
| A quantity past a bound | `LimitError` |

Twelve rows is the longest refusals table here, and one row longer than [Amiga ProTracker's](mod.md):
the header states where a song starts and nothing about where it resumes.
[`limits.md`](../limits.md) states the bounds behind the last of them.

## Effect commands

A command is one nibble printed as `0`–`9` and then `A` onwards, followed by one parameter byte.

| | | |
|---|---|---|
| `0` arpeggio | `2` portamento down | `C` set volume |
| `1` portamento up | `B` position jump | `D` pattern break |
| | | `F` set speed |

Seven of the sixteen the nibble reaches, which is what makes this the smallest command set here. Amiga
ProTracker filled the rest and kept these seven at the numbers they hold, so a song written under either
reads the same. `D` reads its parameter a decimal digit to each nibble, so a break to row 16 is stored as
`0x16`.

`F` sets the ticks a row lasts and nothing else. The second half Amiga ProTracker gave it — a parameter
at or above `0x20` setting the beats per minute — arrived with that format, along with `A`, the `E`
sub-commands, and the rest of the vocabulary.

See [`effects.md`](../effects.md) for the shared vocabulary these spell.

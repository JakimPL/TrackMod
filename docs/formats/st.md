# Soundtracker (`.mod`)

Ultimate Soundtracker, by Karsten Obarski, was published in 1987 for the Amiga. It was the first program to
store a song's patterns, its order list and its sampled sounds in one file, and this whole family of
trackers begins with it. Several trackers wrote the same layout after it, and Amiga ProTracker grew out of
them three years later. A file holds fifteen sampled sounds. A cell names one of them, and the key the
cell plays it at is the pitch it sounds.

The header is a fixed block of 600 bytes. That choice shapes everything below.

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

Every offset is arithmetic. A section begins where the sizes of the sections before it put it. The pattern
width is known before any byte is read, because every module of this format plays the four channels the
machine had. A reader finds a pattern by multiplying its three dimensions and finds the waveforms by adding
up all the patterns.

**The file length identifies the format.** The file has no tag or magic number, because both arrived with
the trackers that came after. The fifteen sample records give the size of the waveform data at the end of
the file, and the order table gives the last pattern before it. A file of this format is exactly as long
as those two add up to behind the header. A file that carries a tag names the tracker that wrote it and is
read as [that format](mod.md).

**A file's pattern count has two sources.** The order table points to the highest pattern a song plays.
The room between the header and the waveforms holds however many patterns were stored. The reader takes the
larger of the two, which keeps both, and needs that count to find the waveforms at the right offset.

## Order list

The header gives the number of positions that play in one byte at offset 470. The table always occupies its
full 128 bytes, and each byte is the number of the pattern at that position. A song plays from its first
position through to the count, and then starts again at the beginning.

The parser moves a count above the 128 the table holds back down to 128. It drops a position that points to
a pattern missing from the file. It reports both.

## Patterns

A pattern is 64 rows with one four-byte cell per channel. Every cell is written, whether or not it holds
anything. The stream starts directly with the cells and runs to the end of the grid, so a pattern takes
1024 bytes whatever it holds, and a reader finds it by arithmetic.

Each cell packs its four columns into its four bytes:

| Byte | Bits | The cell holds |
|---|---|---|
| 0 | `0xF0` | the sample number's high nibble |
| 0 | `0x0F` | the period's four high bits |
| 1 | all | the period's eight low bits |
| 2 | `0xF0` | the sample number's low nibble |
| 2 | `0x0F` | the effect command |
| 3 | all | the effect parameter |

Fifteen samples fit in the low nibble alone. Amiga ProTracker used the high nibble for the sixteen slots it
added. A run of cells that ends before the grid does leaves the rest of the grid silent, which is how a
player sounds it. The parser reports this.

### The note column

The column holds an **Amiga period**: the divider the sound chip plays a sample out at, so the column is
purely a pitch. Three octaves are tabulated, 856 down to 113, and those thirty-six keys are all this
format's own trackers wrote. The twelve bits a cell allows for the field reach further, to shared keys 21
to 119, so a file with a scaled period is read at the key that period names.

Each tracker of this family wrote its own table, and the tables differ in the last digit. The reader
therefore maps a period to the key it comes closest to, and a pattern reports once how many periods it
moved. A period further than half a semitone from every key is a pitch outside the tabulated octaves and
reads as an absent note.

### The instrument column

The column is **one-based**: the two nibbles join into a sample number `n`, which points to position `n - 1`.
The value `0` leaves the channel on the sample it already plays. A cell that names a sample past the
fifteen the file holds is read as naming none, so its channel keeps its current sample, and the parser
reports it.

## Samples

A 30-byte sample record holds a 22-byte name, a length, a finetune, a volume and one loop. Amiga ProTracker
kept the same record. **The length counts pairs of frames**, so a record holds half the byte count of a
waveform, which is eight-bit and one channel throughout. A module writes all fifteen records, whether the
song fills them or leaves them empty, so one more sample costs its frames and nothing else.

**A loop start is counted in bytes here.** The trackers after this one count the same field in pairs. The
loop length counts pairs in both. A loop length of one pair means the sample plays through once, so a real
loop is at least two pairs long. When writing a loop, the writer extends its end to the pair that closes
it, which keeps every frame the loop repeats inside the region the record names.

The parser moves a loop that reaches past the frames the file holds back inside them and sets a volume
above full to full. It reports both.

The trackers of this format shipped a sample library and wrote the source name of each waveform into its
record, so a slot without a waveform can still hold text the file means to keep. A song therefore holds
every slot up to the last one that has anything in it: a waveform, a name, or a cell that names it.

### Tuning

The writer sets the finetune byte to zero, and every sample plays its own key at the untrimmed 8363 Hz.
Amiga ProTracker grew the field into sixteen rows of periods an eighth of a semitone apart. This format
reads the byte on that same lattice, so a file that sets one keeps it, and a rate recorded off the lattice
is graded against it.

## Later additions

The trackers that followed Ultimate Soundtracker wrote this same layout and used more of the effect nibble,
which is where `B`, `C`, `D` and `F` below come from. Their files look identical, so a file cannot show
which of them wrote it. A cell that holds a command none of them numbered keeps its bytes, for whoever
knows what they mean.

The byte after the order count is where these trackers wrote a speed of their own, in units that each
tracker read its own way. The format keeps a file's byte in its settings and writes it back as it stood. A
song built from nothing gets the 120 that every module of this format opens on.

## Timing

The clock is the machine's. A module runs at the clock every tracker of this family uses: six ticks a row
at 125 beats per minute. A row lasts `speed × 5 / (2 × tempo)` seconds, so at 44100 Hz and speed 1 the
shortest whole-frame row this format reaches is 882 frames, because the tempo stays at 125.

This format's capacities fix those two values at 6 and 125. A song that asks to start at other values is
reported against those bounds, and the report shows the clock it asked for. A mid-song `F` can reach only
the five bits a player reads it in.

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
| What names the writer | — |

| Content | Reported as |
|---|---|
| A volume in a cell | `ValueError` |
| A note command of any kind | `ValueError` |
| A song resuming past its first position | `ValueError` |
| A stereo waveform | `ValueError` |
| A sixteen-bit waveform | `ValueError` |
| A per-sample panning | `ValueError` |
| A sustain loop | `ValueError` |
| A loop that plays backward | `ValueError` |
| A loop over a waveform of one pair of frames | `ValueError` |
| An effect command past the four bits a cell holds | `ValueError` |
| A song whose cells name instruments | `ValueError` |
| A quantity past a bound | `LimitError` |

This table has twelve rows, one fewer than [Amiga ProTracker's](mod.md) thirteen. Amiga ProTracker adds two
rows for the tag, which come up while reading. This format adds one row of its own, because its header
gives where a song starts and nothing about where it resumes.
[`limits.md`](../reference/limits.md) lists the bounds behind the last row.

## Effect commands

An effect command is one nibble, written `0`–`9` and then `A` onward. One parameter byte follows it.

| | | |
|---|---|---|
| `0` arpeggio | `2` portamento down | `C` set volume |
| `1` portamento up | `B` position jump | `D` pattern break |
| | | `F` set speed |

The set uses seven of the sixteen values the nibble can hold, which makes it the smallest command set of the
five formats. Amiga ProTracker filled the rest and kept these seven at the same numbers, so a song reads
the same under either. `D` reads its parameter as one decimal digit per nibble, so a break to row 16 is
stored as `0x16`.

Here `F` only sets the ticks a row lasts. Amiga ProTracker added the second half of it: a parameter at or
above `0x20` sets the beats per minute. That format also introduced `A`, the `E` sub-commands and the rest
of the vocabulary.

See [`effects.md`](../reference/effects.md) for the shared vocabulary these commands spell.

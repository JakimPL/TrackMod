# The formats

This directory holds one document per format. Each uses the same headings, so the set can be compared side by
side and one more format is one more file. [`documentation.md`](../contributing/documentation.md) explains
the template and the two tables every document carries. This page is the index. It also lists the places
where one field means different things in different formats.

| Format | Document | A cell's instrument column names | Sections are found by | One instrument |
|---|---|---|---|---|
| Impulse Tracker `.it` | [`it.md`](it.md) | a sample or an instrument | three tables of offsets | `.iti` |
| FastTracker 2 `.xm` | [`xm.md`](xm.md) | an instrument | walking sizes, front to back | `.xi` |
| Amiga ProTracker `.mod` | [`mod.md`](mod.md) | a sample | walking fixed sizes, front to back | — |
| Scream Tracker 3 `.s3m` | [`s3m.md`](s3m.md) | a sample | two tables of paragraph numbers | — |
| Soundtracker `.mod` | [`st.md`](st.md) | a sample | walking fixed sizes, front to back | — |

## Where they disagree about the same field

Almost everything a song holds means the same thing in every format, and each format writes it in its own
bytes. The exceptions are fields with one name and several behaviors. Check them when you write one piece
of music to more than one format.

| Field | Impulse Tracker | FastTracker 2 | Amiga ProTracker | Scream Tracker 3 | Soundtracker |
|---|---|---|---|---|---|
| A stored key | the key's own number | one above the shared numbering | the period the pitch sounds at | an octave over a semitone | the period the pitch sounds at |
| Note column commands | off, cut, fade | key off | — | cut | — |
| Pattern width | recovered from the cell stream | given in the header | given by the tag | given in the channel table | the four the machine played |
| A silent pattern costs | `rows + 2` bytes | `rows × channels` | `rows × channels × 4` | `rows` | `rows × channels × 4` |
| Sample table | one, shared by every instrument | one copy per owning instrument | thirty-one fixed slots | one, addressed by every cell | fifteen fixed slots |
| Sample gain | a multiplier, `0..64` | the level baked into the waveform | the level baked into the waveform | the level baked into the waveform | the level baked into the waveform |
| The header's clock | a speed byte and a tempo byte | two sixteen-bit fields | the clock the lineage starts on | a speed byte and a tempo byte | the clock the lineage starts on |
| What names the writer | a number, and a mark in four reserved bytes | twenty bytes of text | the tag's family | a number, and a mark in eight reserved bytes | — |
| An absent volume | the mask bit leaves the column out | the byte `0x00` | — | the marker bit leaves the column out | — |
| Volume-column rates | ten steps | sixteen steps | — | — | — |
| Volume-column panning | 65 positions | 16 positions | — | 65 positions | — |
| Envelope points | 25 | 12 | — | — | — |
| Envelope sustain | a span of points | one point | — | — | — |
| A fade begins | where the volume envelope ends | at the key off | — | — | — |
| Fade counter | 1024 | 32768 | — | — | — |

The first seven rows apply to all five formats. The rows below them apply to the formats that keep a volume
column, instrument records, or a field that names the program that wrote a file. The six paragraphs below
explain these differences in more detail.

**Each format spells its own note commands.** Impulse Tracker spells three of them, FastTracker 2 spells the
key off and Scream Tracker 3 spells the cut. The two Amiga formats store only a pitch period in that column.
A voice that must end the same way everywhere is therefore ended by a cell that holds no note at all.
Instruments differ in the same way: only two of the five formats keep records for one.

**A key travels only as far as the narrowest column allows.** Impulse Tracker numbers ten octaves and
stores a key as its own number. FastTracker 2 numbers eight octaves, counting from one. Scream Tracker 3
counts its octaves from the model's second octave, so a cell that asks for one of the twelve deepest keys
is refused by name. The two Amiga formats store the period a pitch sounds at, and its twelve bits reach
shared keys 21 to 119.

**A fade travels as a curve.** The two fade counters differ by a factor of 32, so the same number gives two
different lengths. The two starting points differ by the length of the volume envelope. To play a voice
down the same way in both formats, use the envelope curve and leave the fade to whatever the release needs.

**A shared waveform costs one slot per owner in FastTracker 2.** Impulse Tracker stores one sample table
that the whole song addresses. FastTracker 2 gives every instrument its own copies. A song whose two
instruments play one waveform therefore comes back from `.xm` holding two waveforms, and the file grows by
the size of the second one.

**An amount travels only as far as both grids reach.** A volume-column rate keeps the value its column
stores, on the grid its own format counts in, so nine is the largest portable amount. Panning in the volume
column is coarser in FastTracker 2 than in the other two formats that have it: sixteen positions against
sixty-five.

**Silence has a price, and each format charges a different one.** A pattern of pure silence costs one byte
a row where a stream lists only what plays. It costs one byte a cell, or four in the Amiga lineage, where
a grid writes every position down. This one number sums up the difference between the two ways of storing a
pattern.

[`limits.md`](../reference/limits.md) lists every bound behind these, [`volume.md`](../reference/volume.md)
describes the columns, and [`model.md`](../reference/model.md) describes what the shared model holds that
any one format may leave out.

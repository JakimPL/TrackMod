# The formats

One document per format, each written to the same headings so that the set is diffable and a fifth format
is one more file. [`conventions.md`](../conventions.md) states the template and the two tables every one of
them carries; this page is the index, and the short list of places where the same field means two things.

| Format | Document | A cell's instrument column names | Sections are found by | One instrument |
|---|---|---|---|---|
| Impulse Tracker `.it` | [`it.md`](it.md) | a sample or an instrument | three tables of offsets | `.iti` |
| FastTracker 2 `.xm` | [`xm.md`](xm.md) | an instrument | walking sizes, front to back | `.xi` |
| Amiga ProTracker `.mod` | [`mod.md`](mod.md) | a sample | walking fixed sizes, front to back | — |
| Scream Tracker 3 `.s3m` | [`s3m.md`](s3m.md) | a sample | two tables of paragraph numbers | — |

## Where they disagree about the same field

Almost everything a song carries means the same thing in every format and is written by each in its own
bytes. These are the exceptions — one name, several behaviours — and they are what to check when one piece
is written to more than one of them.

| Field | Impulse Tracker | FastTracker 2 | Amiga ProTracker | Scream Tracker 3 |
|---|---|---|---|---|
| A stored key | the key's own number | one above the shared numbering | the period the pitch sounds at | an octave over a semitone |
| Note column commands | off, cut, fade | key off | — | cut |
| Pattern width | recovered from the cell stream | stated in the header | named by the tag | stated in the channel table |
| A silent pattern costs | `rows + 2` bytes | `rows × channels` | `rows × channels × 4` | `rows` |
| Sample table | one, shared by every instrument | one copy per owning instrument | thirty-one fixed slots | one, addressed by every cell |
| Sample gain | a multiplier, `0..64` | the level baked into the waveform | the level baked into the waveform | the level baked into the waveform |
| The header's clock | a speed byte and a tempo byte | two sixteen-bit fields | the clock the lineage starts on | a speed byte and a tempo byte |
| An absent volume | the mask bit leaves the column out | the byte `0x00` | — | the marker bit leaves the column out |
| Volume-column rates | ten steps | sixteen steps | — | — |
| Volume-column panning | 65 positions | 16 positions | — | 65 positions |
| Envelope points | 25 | 12 | — | — |
| Envelope sustain | a span of points | one point | — | — |
| A fade begins | where the volume envelope ends | at the key off | — | — |
| Fade counter | 1024 | 32768 | — | — |

The first seven rows are answered by all four formats, and the rows below them belong to the ones keeping
a volume column or instrument records. The six that follow are the ones worth reading twice.

**No note command travels the whole set.** Impulse Tracker spells three of them, FastTracker 2 the key
off, Scream Tracker 3 the cut and Amiga ProTracker none, so the four vocabularies share nothing: a voice
ended the same way everywhere is one ended by a cell that states no note at all. An instrument is the
same story from the other side — two of the four keep records for one.

**A key travels as far as the deepest column reaches.** Impulse Tracker numbers ten octaves and stores a
key as its own number. FastTracker 2 numbers eight of them from one. Scream Tracker 3 counts its octaves
from the model's second, so the twelve deepest keys move up an octave to be stored, and Amiga ProTracker
stores the period a pitch sounds at, whose twelve bits reach shared keys 21 to 119.

**A fade is not portable.** The two counters differ by a factor of 32, so the same number means two
lengths, and the two starting points differ by however long the volume envelope runs. A voice worth
playing down the same way in both is worth playing down by the envelope curve, with the fade left to
whatever the release needs.

**A shared waveform costs one slot per owner in FastTracker 2.** Impulse Tracker stores a sample table the
whole song addresses; FastTracker 2 gives every instrument its own copies. A song whose two instruments
play one waveform therefore comes back from `.xm` holding two waveforms, and grows by the size of the
second one.

**An amount travels as far as both grids reach.** A volume-column rate is carried as the column stores it,
on the grid its own format counts in, so nine is as far as a portable amount goes. Panning in the volume
column is coarser in FastTracker 2 than in the other two that carry it: sixteen positions against
sixty-five.

**Silence has a price, and each format names a different one.** A pattern of pure silence costs one byte a
row where a stream lists only what plays, and one byte a cell — four in Amiga ProTracker — where a grid
writes every position down. That is the whole difference between the two ways of storing a pattern, in one
number.

[`limits.md`](../limits.md) states every bound behind these, [`volume.md`](../volume.md) the columns, and
[`model.md`](../model.md) what the shared model holds that any one format may leave out.

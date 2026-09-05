# The formats

One document per format, each written to the same headings so that the set is diffable and a fifth format
is one more file. [`conventions.md`](../conventions.md) states the template and the two tables every one of
them carries; this page is the index, and the short list of places where the same field means two things.

| Format | Document | A cell's instrument column names | Sections are found by | One instrument |
|---|---|---|---|---|
| Impulse Tracker `.it` | [`it.md`](it.md) | a sample or an instrument | three tables of offsets | `.iti` |
| FastTracker 2 `.xm` | [`xm.md`](xm.md) | an instrument | walking sizes, front to back | `.xi` |

## Where they disagree about the same field

Almost everything a song carries means the same thing in both formats and is written by each in its own
bytes. These are the exceptions — one name, two behaviours — and they are what to check when one piece is
written to both.

| Field | Impulse Tracker | FastTracker 2 |
|---|---|---|
| A fade begins | where the volume envelope ends | at the key off |
| Fade counter | 1024 | 32768 |
| Sample table | one table, shared by every instrument | one copy per owning instrument |
| Volume-column rates | ten steps | sixteen steps |
| Volume-column panning | 65 positions | 16 positions |
| Envelope sustain | a span of points | one point |
| Envelope points | 25 | 12 |
| A stored key | the key's own number | one above the shared numbering |
| Pattern width | recovered from the cell stream | stated in the header |
| An absent volume | the mask bit leaves the column out | the byte `0x00` |
| Sample gain | a per-sample multiplier, `0..64` | the level baked into the waveform |

Three of those reach the sound itself; the rest settle in the bytes.

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
column is coarser still: sixteen positions against sixty-five.

[`limits.md`](../limits.md) states every bound behind these, [`volume.md`](../volume.md) the columns, and
[`model.md`](../model.md) what the shared model holds that either format may leave out.

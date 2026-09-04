# FastTracker 2 (`.xm`)

Written by `trackmod.trackers.xm.writer.write_module`, read by `trackmod.trackers.xm.parser.ModuleReader`, bound together
by `trackmod.trackers.xm.module.XMModule`.

It is the opposite of Impulse Tracker in nearly every decision, which is what makes the pair a fair test
of the shared model.

## File shape

There are no offset tables. Every section is found by walking the sizes of the ones before it, so the
file is one concatenation read strictly front to back:

```
"Extended Module: " header                  80 bytes
order table                                 always 256 bytes, whatever the song plays
patterns                                    9-byte header + cell stream, one after another
instruments                                 header, then its sample headers, then its waveforms
```

The header's `header_size` at offset 60 counts from that offset onward and covers the rest of the header
plus the whole order table. The order table is written at its full 256 bytes even when the song plays
three positions, and `restart_position` says where playback resumes.

An instrument is self-contained: its header, then every sample header it owns, then every waveform, in
that order.

## Packed patterns

Every cell of every row is stored and nothing terminates a row, so a player reads exactly
`rows * channels` cells. There is **no memory between cells**: what a cell states is what the grid holds.

The first byte of a cell decides how it is read:

- **High bit set** — the byte is a mask, and only the columns it names follow:

  | Bit | Column |
  |---|---|
  | `0x01` | note |
  | `0x02` | instrument |
  | `0x04` | volume |
  | `0x08` | effect command |
  | `0x10` | effect parameter |

- **High bit clear** — the byte *is* the note, and all five columns follow uncompressed.

A cell stating every column therefore costs five bytes in the uncompressed form and would cost six with
a mask, so a full cell drops its mask. A cell stating nothing still costs the one byte its empty mask
occupies.

That absence of memory collapses the size model to a closed form. `trackmod.trackers.xm.patterns.sizing` counts
how many columns each grid position states and evaluates

```
5 if all five are stated else 1 + count
```

over the whole grid at once — no walk, no channel state. Compare `trackmod/trackers/it/patterns/sizing.py`, which
needs a run-length comparison per column per channel to answer the same question.

Notes are stored one **above** the shared numbering: key `k` is byte `k + 1`, and byte `97` is a key off.
The eight octaves this format numbers are keys `0..95`; the shared model numbers ten, so a key above 95
is reported against `Capability.NOTE`. There is no cut and no fade in the note column, so a `NoteCommand`
other than `OFF` raises.

Instrument numbers are one-based here too, with zero meaning "stay on the instrument this channel already
carries".

The volume column stores a level as `0x10 + level`, and spends the rest of its byte on the effects it
also carries — volume slides, fine slides, a vibrato speed and depth, panning, panning slides and a
portamento. Each occupies a run of sixteen values, and `trackmod.trackers.xm.spec.volume` states those
runs as data. `0x00` is what a cell stating every column writes where it holds no volume, so that byte
reads as an absence; the bytes between it and the level range name nothing this format defines and read
the same way, reported once for a whole pattern. See [`volume.md`](../volume.md).

## Tuning: how a rate becomes a transposition

FastTracker 2 stores no playback rate. A sample sounds at the pitch of the key that triggers it, shifted
by `relative_note` whole semitones and trimmed by `finetune` in units of `1/128` of a semitone. Under the
linear frequency table the playback frequency for key `k` is

```
frequency = 8363 * 2 ** ((k + relative_note + finetune / 128 - 48) / 12)
```

`trackmod.trackers.xm.tuning` inverts this. Given a rate in hertz, the key that triggers a sample and the note
that key should sound, it solves

```
128 * relative_note + finetune = pitch_units(rate) + 128 * (sounded - 60 - key)
```

taking the remainder toward negative infinity so the finetune trim is always positive and a whole-semitone
tuning spends nothing on it. Key 60 is C-5, the key at which a sample plays at exactly its recorded rate,
which is what `Sample.rate` means.

```python
tuning_for(44100, key=Note(24), sounded=Note(60))   # relative_note=52, finetune=100
```

**The lattice is coarse and it rounds.** `1/128` of a semitone is 0.78 cents, so a rate is stored to
within half of that — 0.39 cents, or about 226 ppm. A sample recorded at 44100 Hz comes back as 44092 Hz:
181 ppm flat, 0.31 cents. That is inaudible as pitch and irrelevant to a musical sample, but it is real
and it matters to a caller reconstructing a signal frame by frame. `xm/spec/ranges.py` derives the
format's whole reachable rate range, `10 Hz` to `25662141 Hz`, from the signed-byte relative note.

A test pins the derivation against the two hardcoded constants the exporter this library replaced used,
for all sixteen of its sample slots.

## Instruments own their samples

There is no shared sample table. Each instrument carries **its own copies** of the samples its keys
reach. A sample two instruments both play is written twice, and `size().pcm` counts it twice —
`trackmod.trackers.xm.sizing` is explicit about charging that cost.

That is what the shared `sample` count in `trackmod.trackers.xm.spec.storage.XM_STORAGE` means here: a
slot is charged once per owner rather than once per waveform, and a sample no key reaches costs nothing
at all. `empty_instrument` carries the 29-byte short header below, against the 263-byte long form.

`trackmod.trackers.xm.instruments.grouping` derives the arrangement from the shared model's keymaps:

- `local_slots` assigns each sample a position within the instrument, in the order the keys first name
  it;
- `slot_tuning` finds the one transposition serving every key routed to a sample. A stored sample is
  transposed once, so keys sounding their own pitch always agree, and so does a whole-instrument
  transposition. A keymap shifting one key of a sample differently from another is asking for something
  the format has no field for, and raises.

A consequence worth expecting: reading a module back gives one instrument per group, not the arrangement
it was built from. A song whose two instruments shared a sample comes back with two samples.

The keymap block is 96 bytes, one sample position per key. There is no way to leave a key silent — every
byte names a position, and an instrument owning no samples simply never plays.

An instrument that owns nothing is written in the short **29-byte** header the format reserves for it,
which stops after the sample count rather than reserving room for a keymap nothing routes through. Those
29 bytes are literally the opening of the 263-byte long form, which is what makes placeholder instrument
slots cheap.

## One instrument on its own (`.xi`)

The same instrument makes a file of its own, written by
`trackmod.trackers.xm.instruments.writer.write_instrument_file` and bound by
`trackmod.trackers.xm.instrument_file.XMInstrumentFile`:

```
"Extended Instrument: "                     21 bytes
instrument name                             22 bytes
0x1A, tracker name, version 0x0102          23 bytes
keymap, envelopes, vibrato, fadeout         the body, to offset 296
sample count                                2 bytes, closing a 298-byte header
sample headers                              40 bytes each
sample frames                               deltas, in header order
```

Behind its own identity block the file lays out **the same body a module's instrument header does**,
moved on by the 33 bytes the two identity blocks differ by — so `layout.instrument.body_fields` describes
it once and each record states how far in its body begins. The sample count sits last here and third in a
module, and the samples that follow are grouped exactly as a stored instrument owns them, each carrying
the transposition that sounds its keys at the pitch the shared model asks for.

```python
from trackmod.core.instruments.transfer import extract
from trackmod.trackers.xm.instrument_file import XMInstrumentFile
from trackmod.limits.compliance import Compliance

unit = extract(song, 0)
XMInstrumentFile.from_unit(unit, compliance=Compliance.CANONICAL).save(Path("piano.xi"))
```

The bounds are the format's own, so a sample staged below full gain is reported here exactly as it is in
a module — the field is absent from the format, whichever container the sample travels in.

## Envelopes

Two envelopes, volume and panning, each of at most 12 points, values `0..64`, with the point table and
its count, sustain point, loop bounds and flags scattered across the instrument header at fixed offsets.
There is no pitch envelope, and an instrument carrying one raises.

The sustain is a **single point**, not a span, so an `Envelope` whose sustain span covers more than one
point raises. The flag bits also sit in the opposite order to Impulse Tracker's: here sustain is `0x02`
and loop is `0x04`.

## Fadeout

`trackmod.trackers.xm.fade` binds the shared fade to this format's counter, which is **32768**: a fading
voice loses `fadeout` from it every tick, so it falls silent after `32768 / fadeout` ticks. The tracker's
own editor counts a fadeout to `0xFFF`, whose eight ticks are the quickest fade it states.

The fade starts at the **key off**, wherever the volume envelope has reached. A voice with no volume
envelope at all is stopped by the key off instead, so a fade to state is a fade with a curve to state it
against. Both were verified by rendering; Impulse Tracker begins the same fade elsewhere, which is worth
knowing when one song is written to both.

## Samples

`SAMPLE_HEADER` is 40 bytes and its lengths count **bytes rather than frames**, so a 16-bit sample's
stored length is twice its frame count. The loop mode is the low two bits of the type byte and the
16-bit flag is `0x10`. There is no sustain loop, and a sample carrying one raises. There is no stereo
storage either, and a sample carrying two channels raises.

Frames are stored as **deltas**: successive differences that the player integrates with a running sum in
the stored width. `trackmod.binary.pcm.codec` takes the differences in a wider type and casts back, so a
difference that overshoots the signed range wraps exactly as the player's running sum unwraps it. The
first stored delta is taken against zero, which makes it the waveform's first absolute amplitude.

There is no per-sample gain and no per-instrument volume, which is why `Capability.SAMPLE_GAIN` and
`Capability.INSTRUMENT_VOLUME` are pinned to full — see [`limits.md`](../limits.md).

## Timing

`trackmod.trackers.xm.timing` binds the shared clock to a sixteen-bit speed and a sixteen-bit tempo. That is this
format's real advantage for a caller working to a frame budget: at 44100 Hz and speed 1 the shortest
whole-frame row it reaches is 2 frames, against Impulse Tracker's 441. Both extremes were verified by
rendering, and both play at exactly the row length the clock computes.

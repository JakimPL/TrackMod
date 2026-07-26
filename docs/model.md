# The domain model

One model describes a piece of tracker music; each format binds it. Everything here lives under
`trackmod/core` and knows nothing about bytes.

## Song

`trackmod.core.songs.song.Song` is the whole piece:

| Field | Meaning |
|---|---|
| `name` | The module title |
| `channels` | How wide every pattern is |
| `patterns` | The grids, indexed by the order list |
| `order` | Which patterns play, in what sequence |
| `instruments` | The playable voices, indexing into `samples` |
| `samples` | The waveforms |
| `playback` | The clock the song starts on |

Patterns, instruments and samples are flat tuples that columns and keymaps index into, so a song is
self-contained. A validator confirms that every pattern is the song's width, every order names a pattern
that exists, and every keymap names a sample that exists.

`OrderList` holds playable positions only — the separator and end-of-song markers a format writes into
its own order table are that format's business — plus a `restart` position. `Playback` holds `speed`
ticks per row at `tempo` beats per minute.

## Pattern

`trackmod.core.patterns.grid.Pattern` is **columnar**: five aligned `(rows, channels)` planes of
`numpy.int16`, one per column, with `EMPTY = -1` marking an absent value.

```
note  instrument  volume  effect  parameter
```

Keeping the columns apart rather than storing cell objects is what gives per-column presence. A key-off
carries a note and nothing else; a mid-pattern tempo change carries only an effect. It also lets the
packers and the size models read whole planes at once, which is why measuring a pattern's packed length
costs a vectorised pass rather than a walk over the grid.

`Pattern` is frozen. Authoring happens through `trackmod.core.patterns.builder.PatternBuilder`, which
fills the grid cell by cell and freezes it with `build()`. Beyond `place(row, channel, cell)` it offers
`free_effect_channel(row)`: the lowest channel on a row whose effect column is still free, which is
where a global effect such as a tempo change belongs.

`Pattern.widened(channels)` pads a grid with silent channels, which formats storing one channel count
for the whole module need.

## Cell

`trackmod.core.patterns.cell.Cell` gathers one grid position:

```python
Cell(note=Note(60), instrument=0, volume=64, effect=Effect(command=1, parameter=6))
```

Each of the four is independently `None`. `instrument` is a **zero-based** index into `song.instruments`;
both formats number their instrument column from one and their writers add the offset, because zero is
what a stored cell writes to leave a channel on the instrument it already carries.

## Notes

`trackmod.core.notes.pitch.Note` is a key counted in semitones above C-0, in `0..119`. That is Impulse
Tracker's numbering; FastTracker 2 stores the same key one higher. The tracker octave is one above the
MIDI octave of the same pitch, so tracker C-5 is MIDI 72 and `Note.from_midi(m) == Note(m - 12)`.

`trackmod.core.notes.command.NoteCommand` covers the note-column entries that act on a playing voice
instead of starting a pitch — `OFF`, `CUT`, `FADE`. Their values continue past the key range, so one
integer plane holds either kind and `NoteValue = Note | NoteCommand`.

## Samples

`trackmod.core.samples.sample.Sample` carries float PCM in `[-1, 1]`, a `rate` in **hertz**, a
`BitDepth`, two loops, and three levels:

| Field | Meaning |
|---|---|
| `volume` | The level a cell with no volume column plays at |
| `gain` | A fixed multiplier applied on top of whatever level plays |
| `panning` | A position on the shared `0..255` field, or `None` to leave it to the tracker |

Recording the rate in hertz rather than in a format's own units is what lets one song serve both: one
format stores the frequency outright, the other stores a transposition of the triggering key, and each
writer derives its own encoding. A sample with no frames is a valid placeholder slot.

`gain` is where a format's absence of a feature becomes visible rather than silent: FastTracker 2 has no
per-sample multiplier, so it bounds `gain` to full and reports anything quieter, telling a caller the
scaling has to be baked into the waveform.

## Instruments

`trackmod.core.instruments.instrument.Instrument` is a named routing of keys onto samples, plus the
envelopes every voice it starts follows, a fadeout, a level, a panning and the new-note and duplicate
behaviours.

A `Keymap` is exactly 120 entries, one per key, each either `None` or a `KeyAssignment`:

```python
KeyAssignment(sample=2, note=Note(60))
```

Separating the **pressed key** from the **sounded note** is what lets an instrument route keys to samples
without transposing them: every key can name the same note and still select a different sample.
`pitched_keymap(sample=…)` gives every key its own pitch; `routed_keymap({…})` answers only the keys
named and leaves the rest silent.

`Envelope` is a breakpoint curve with optional `loop` and `sustain` spans over point indices. An
instrument carrying no envelope of a kind leaves that property alone, so absence rather than a flag is
what switches an envelope off.

## Timing

Both formats share one clock: a tick lasts `5 / (2 * tempo)` seconds and a row lasts `speed` ticks, so a
row spans

```
speed * 5 * frame_rate / (2 * tempo)
```

frames. `trackmod.core.timing.lattice` works in that exact rational rather than in floating point, which
matters when a caller derives a block length from the row instead of rounding one to fit:

- `row_frames(speed, tempo, frame_rate=…, speed_bound=…, tempo_bound=…)` — the whole frames one row
  spans, raising when the pair gives a fractional row;
- `exact_timings(...)` — every tempo whose row is a whole number of frames at one speed, ordered by row
  length;
- `nearest_timing(target_frames, ...)` — the closest achievable row length, resolving ties to the
  shorter row.

Each format package re-exposes these three bound to its own speed and tempo ranges, as
`trackmod.trackers.it.timing` and `trackmod.trackers.xm.timing`. The ranges are the whole difference: at 44100 Hz and
speed 1 the shortest whole-frame row Impulse Tracker reaches is 441 frames, while FastTracker 2's
sixteen-bit tempo reaches 2.

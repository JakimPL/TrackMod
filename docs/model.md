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
for the whole module need. A padded channel is carried through a file as such: `.xm` stores a full grid,
and `.it` names its widest channel in the cell stream, so `channels` reads back as it was declared.

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

### A curve stated in time

An envelope stores **ticks**, and a tick's length follows the tempo, so one curve written for two clocks
is two envelopes. `trackmod.core.envelopes.curve` states a curve in the terms it was measured in and
binds it to a clock:

```python
from trackmod.core.envelopes.curve import Breakpoint, timed_envelope

decline = timed_envelope(
    (
        Breakpoint(seconds=0.0, value=64),      # the onset, at the level the waveform was stored at
        Breakpoint(seconds=0.5, value=64),      # still there where the loop takes over
        Breakpoint(seconds=3.0, value=16),      # the level the recording fell to
    ),
    tempo=125,
    tick_bound=limits.bound(Capability.ENVELOPE_TICK),
    value_bound=limits.bound(Capability.ENVELOPE_VALUE),
    sustain=EnvelopeSpan(begin=2, end=2),
)
```

Each breakpoint lands on the tick its time falls on and each value on the grid the format numbers. The
ticks come out ascending whatever was asked for: two breakpoints inside one tick are moved apart, and a
curve reaching past the last tick a format counts is drawn back into the ticks that remain, so the end of
a curve stays stated. `envelope_seconds(envelope, tempo=…)` is the way back, for measuring what a stored
curve does against the trajectory it was fitted to.

Because those ticks belong to a tempo, an instrument travelling on its own is worth keeping beside the
tempo its envelopes were fitted at: an `.iti` or an `.xi` carries a curve and no clock to read it by.

### Fading a released voice

`fadeout` is a **rate**, not a length of time. A voice being faded carries a counter that starts full and
drops by the instrument's fadeout every tick, and what remains of it scales the level the voice plays at,
so the time it buys is `counter / fadeout` ticks. The counter's size is each format's own, so
`trackmod.core.instruments.fade` takes it as a parameter and each format binds its own — the same shape
`timing` has:

```python
from trackmod.trackers.it.fade import fade_seconds, fadeout_value

fadeout_value(0.25, tempo=125)   # 82, the rate that fades a released voice out in a quarter second
fade_seconds(82, tempo=125)      # 0.2498…, the same number read the other way
```

`NO_FADEOUT` leaves the counter full, which is a voice that keeps its level for as long as it sounds and
reads as a fade of unbounded length. A fade slower than a counter step of one raises rather than rounding
onto that value, since zero states the opposite of a slow fade. **When** the fade begins is each format's
own convention, stated in the format documents.

## Carrying an instrument between songs

A keymap names positions in the sample table of the song it belongs to, so an instrument on its own is
half a voice. `trackmod.core.instruments.unit.InstrumentUnit` holds the other half — the samples its
keys reach, numbered from zero — and `trackmod.core.instruments.transfer` moves units in and out of
songs:

```python
unit = extract(song, 0)                        # the instrument and the waveforms it sounds
voices = held(song)                            # the same, for every instrument the song numbers
instruments, samples = combine([unit, other])  # one flat table, each keymap restated against it
```

`combine` returns exactly the `instruments=` / `samples=` pair `Song` takes. The renumbering itself is
`Instrument.rerouted(positions)`, which moves the routing and leaves every envelope, level and
behaviour as stated — so an instrument lifted out of one module and written into another sounds what it
sounded before.

Each unit keeps its own copy of a waveform another unit also holds. Impulse Tracker stores that table as
written; FastTracker 2 gives every instrument its own copies regardless, so a shared waveform costs one
slot per owner there either way (see [`formats/xm.md`](formats/xm.md)).

A unit is also what each format stores on its own, as an `.iti` or an `.xi`:

```python
unit = ITInstrumentFile.load(Path("piano.iti")).unit    # one voice, ready to graft
XMInstrumentFile.from_unit(unit, compliance=Compliance.CANONICAL).save(Path("piano.xi"))
```

`trackmod.module.instrument.InstrumentFile` is the protocol both bindings answer, the counterpart of
`TrackerModule` for a container holding one voice. The bounds are the format's own, so what an instrument
can carry is the same question in either container.

A caller holding bytes and the extension they were written under reaches the same units without naming a
format, through `trackmod.trackers.registry`:

```python
voices = parse_units(data, extension=".iti")   # one voice, from a standalone instrument
voices = parse_units(data, extension=".it")    # every voice a module numbers
```

Four extensions are read — `.it` and `.xm` for modules, `.iti` and `.xi` for one instrument — in either
capitalisation, and `MODULE_EXTENSIONS` / `INSTRUMENT_EXTENSIONS` name which is which. This is what lets
a consumer accept whichever container a producer of sampled instruments ships and hold the suffix table
once, here.

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

The same clock read in seconds is `trackmod.core.timing.clock`:

- `tick_seconds(tempo)` — `5 / (2 * tempo)`, the unit envelope breakpoints and note fades are counted in;
- `row_seconds(speed, tempo)` — `row_frames` asked in seconds, for material laid out in time;
- `elapsed_ticks(seconds, tempo)` — the whole tick a duration falls on.

A caller fitting material to a whole-frame lattice works in frames; one placing a breakpoint or a fade
works in ticks. These turn either into the other, and they are why the tempo travels with anything an
instrument states about time.

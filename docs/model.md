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
| `voices` | What a cell's instrument column names |
| `playback` | The clock the song starts on |

Patterns and voices are flat tuples that the order list and the instrument column index into, so a song
is self-contained. A validator confirms that every pattern is the song's width, that every order names a
pattern that exists, and that every value in every instrument column names a voice that exists.

`OrderList` holds playable positions only — the separator and end-of-song markers a format writes into its
own order table are that format's business — plus a `restart` position. `Playback` holds `speed` ticks per
row at `tempo` beats per minute.

## Voices

Every tracker's cell carries an instrument column, and what the number in it names differs by format.
Amiga ProTracker and Scream Tracker 3 name a **sample**. FastTracker 2 names an **instrument**, which
routes keys onto samples of its own. Impulse Tracker names either, and says which in one header bit. The
model states that as a union of two tables, one per way of addressing:

```python
class SampleVoices(BaseModel):
    samples: tuple[Sample, ...]

class InstrumentVoices(BaseModel):
    instruments: tuple[Instrument, ...]
    samples: tuple[Sample, ...]

Voices = SampleVoices | InstrumentVoices
```

A song carries one or the other, because a file is in one mode throughout. Both answer the same two
questions, so the common path branches nowhere:

- `slots` — how many values the instrument column may name;
- `samples` — the waveforms, which is what sizing and serialisation ask for.

Under `SampleVoices` a key plays its waveform at the pitch it was pressed at, so what a voice does is
decided by the sample alone. Under `InstrumentVoices` the cell reaches an instrument first, and the
keymap, envelopes, fadeout, levels and note behaviours it carries shape every voice it starts.

**Conversion is a call the caller makes.** `trackmod.core.voices.convert` holds the pair:

```python
raised(sample_voices)         # every sample gains an instrument routing every key to it at its own pitch
flattened(instrument_voices)  # every instrument contributes the one waveform its keys reach
```

`raised` always succeeds. `flattened` refuses an instrument that reaches several samples or sounds a key
at another key's pitch, since a table of samples holds no room for either — so turning a FastTracker 2
song into one a sample-addressed format can write is a visible step with a visible failure.

Each format states which tables it writes. Impulse Tracker takes either and states the choice in its
header; FastTracker 2 takes `InstrumentVoices`, and a song carrying the other kind is refused by name.

## Pattern

`Pattern` is **columnar**: five aligned `(rows, channels)` planes of `numpy.int16`, one per column, with
`EMPTY = -1` marking an absent value.

```
note  instrument  volume  effect  parameter
```

Keeping the columns apart is what gives per-column presence. A key-off
carries a note and nothing else; a mid-pattern tempo change carries only an effect. It also lets the
packers and the size models read whole planes at once, which is why measuring a pattern's packed length
costs one vectorised pass.

`Pattern` is frozen. Authoring happens through `trackmod.core.patterns.builder.PatternBuilder`, which
fills the grid cell by cell and freezes it with `build()`. Beyond `place(row, channel, cell)` it offers
`free_effect_channel(row)`: the lowest channel on a row whose effect column is still free, which is where
a global effect such as a tempo change belongs.

`Pattern.widened(channels)` pads a grid with silent channels, which formats storing one channel count for
the whole module need. A padded channel is carried through a file as such, so `channels` reads back as it
was declared.

## Cell

`Cell` gathers one grid position:

```python
Cell(note=Note(60), instrument=0, volume=64, effect=Effect(command=1, parameter=6))
```

Each of the four is independently `None`. `instrument` is a **zero-based** index into `song.voices`, whose
kind decides what it names; every format numbers its own column from one and its writer adds the offset,
because zero is what a stored cell writes to leave a channel on the voice it already carries.

## Notes

`Note` is a key counted in semitones above C-0, in `0..119`. That is Impulse Tracker's numbering;
FastTracker 2 stores the same key one higher. The tracker octave is one above the MIDI octave of the same
pitch, so tracker C-5 is MIDI 72 and `Note.from_midi(m) == Note(m - 12)`.

`NoteCommand` covers the note-column entries that act on a playing voice — `OFF`, `CUT`, `FADE`. Their values continue past the key range, so one integer plane holds either kind and
`NoteValue = Note | NoteCommand`. Which of the three a format spells is its own business, and
[`formats/README.md`](formats/README.md) collects that.

## Volumes

`Cell.volume` holds either a level in `0..64` or a `VolumeCommand` — one of the twelve intents the volume
columns state beside levels, paired with the amount it carries. `VolumeValue = Volume | VolumeCommand` is
the union, and the commands continue past the level range in one integer exactly as the note column's do
past the key range.

The amount is stated on the grid the format's own column counts in, which is what keeps a stored column
reading back as the value it holds. [`volume.md`](volume.md) states the runs each format divides its byte
into and what each of them refuses.

## Samples

`Sample` carries float PCM in `[-1, 1]`, a `rate` in **hertz**, a `BitDepth`, two loops, and three levels:

| Field | Meaning |
|---|---|
| `volume` | The level a cell with no volume column plays at |
| `gain` | A fixed multiplier applied on top of whatever level plays |
| `panning` | A position on the shared `0..255` field, or `None` to leave it to the tracker |

Recording the rate in hertz is what lets one song serve every format: one stores the frequency outright,
another stores a transposition of the triggering key, and each writer derives its own encoding. A sample with no frames is a valid placeholder slot.

`gain` is where a format's own reach becomes visible: FastTracker 2 pins `gain` to full and reports
anything quieter, telling a caller that the scaling belongs in the waveform.

`pcm` is shaped `(frames,)` for a mono waveform or `(frames, 2)` for a stereo one, left channel first. A
stereo waveform shares every field above between its two channels, which is what the formats that store
one give it.

`filename` and `vibrato` are Impulse Tracker's own DOS filename and sample-level auto-vibrato. A format
with room for neither leaves them at their default of an empty name and no vibrato.

## Instruments

`Instrument` is a named routing of keys onto samples, plus the envelopes every voice it starts follows, a
fadeout, a level, a panning and the new-note and duplicate behaviours.

A `Keymap` is exactly 120 entries, one per key, each either `None` or a `KeyAssignment`:

```python
KeyAssignment(sample=2, note=Note(60))
```

Separating the **pressed key** from the **sounded note** is what lets one instrument route keys onto
different samples while every key names the same note.
`pitched_keymap(sample=…)` gives every key its own pitch; `routed_keymap({…})` answers only the keys named
and leaves the rest silent.

`Envelope` is a breakpoint curve with optional `loop` and `sustain` spans over point indices. An
instrument carrying no envelope of a kind leaves that property alone, which is how an envelope is
switched off.

### A curve stated in time

An envelope stores **ticks**, and a tick's length follows the tempo, so one curve written for two clocks is
two envelopes. `trackmod.core.envelopes.curve` states a curve in the terms it was measured in and binds it
to a clock:

```python
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
so the time it buys is `counter / fadeout` ticks. The counter's size is each format's own, so the shared
`fade` functions take it as a parameter and each format's own `fade` module binds it — the same shape
`timing` has:

```python
fadeout_value(0.25, tempo=125)   # 82, the rate that fades a released voice out in a quarter second
fade_seconds(82, tempo=125)      # 0.2498…, the same number read the other way
```

`NO_FADEOUT` leaves the counter full, which is a voice that keeps its level for as long as it sounds and
reads as a fade of unbounded length. A fade slower than a counter step of one raises, since zero
states a fade of unbounded length. **When** the fade begins is each format's
own convention, stated in the format documents.

## Carrying an instrument between songs

A keymap names positions in the sample table of the song it belongs to, so an instrument on its own is
half a voice. `trackmod.core.instruments.unit.InstrumentUnit` holds the other half — the samples its keys
reach, numbered from zero — and `trackmod.core.instruments.transfer` moves units in and out of songs:

```python
unit = extract(song.voices, 0)     # the instrument and the waveforms it sounds
units = held(song.voices)          # the same, for every instrument the table numbers
voices = combine([unit, other])    # one table, each keymap restated against the samples behind it
```

`combine` returns exactly the `voices=` table `Song` takes, and all three work on `InstrumentVoices`,
since a voice a cell names directly is a plain sample and travels as one. The renumbering itself is
`Instrument.rerouted(positions)`, which moves the routing and leaves every envelope, level and behaviour
as stated — so an instrument lifted out of one module and written into another sounds what it sounded
before.

Each unit keeps its own copy of a waveform another unit also holds. Impulse Tracker stores that table as
written; FastTracker 2 gives every instrument its own copies regardless (see
[`formats/README.md`](formats/README.md)).

A unit is also what a format stores on its own, as an `.iti` or an `.xi`:

```python
unit = ITInstrumentFile.load(Path("piano.iti")).unit    # one voice, ready to graft
XMInstrumentFile.from_unit(unit, compliance=Compliance.CANONICAL).save(Path("piano.xi"))
```

`InstrumentFile` is the protocol both bindings answer, the counterpart of `TrackerModule` for a container
holding one voice. The bounds are the format's own, so what an instrument can carry is the same question
in either container.

A caller holding bytes and the extension they were written under reaches the same voices through one call,
whichever format wrote them, in `trackmod.trackers.registry`:

```python
voices = parse_voices(data, extension=".iti")   # one voice, from a standalone instrument
voices = parse_voices(data, extension=".it")    # every voice a module numbers
```

What comes back says which kind of table it is, so the container stops mattering at the point the bytes
are read. `MODULE_EXTENSIONS` and `INSTRUMENT_EXTENSIONS` name which suffix is which, in either
capitalisation, which is what lets a consumer accept whichever container a producer ships.

## Reading a file that states something odd

The model above states what a **well-formed** song is, which is what this library writes. Files written by
real trackers state values outside it — an envelope loop ending before it begins, a sample loop reaching
past the waveform, an order naming a pattern the file leaves out — and refusing to read them would refuse
most of the modules there are.

So a parser draws the value into range and says so. `Repairs` gathers what one parse did, counting repeats
of one repair on one subject once, and reports everything as a single `RepairWarning`:

```
RepairWarning: values drawn into range as the file was read: sample 3: rate 0 read as 8363 Hz;
song: 2 order positions naming no stored pattern dropped
```

Which values a given format repairs is stated in its own document, under the section that reads them.
[`conventions.md`](conventions.md) states the rule the three mechanisms follow: a bound reports a quantity,
a `ValueError` refuses content with no encoding, and a repair reads a file as it stands.

## Timing

Every format here shares one clock: a tick lasts `5 / (2 * tempo)` seconds and a row lasts `speed` ticks,
so a row spans

```
speed * 5 * frame_rate / (2 * tempo)
```

frames. `trackmod.core.timing.lattice` works in that exact rational, which matters when a caller derives a
block length from the row it is fitting material to:

- `row_frames(speed, tempo, frame_rate=…, speed_bound=…, tempo_bound=…)` — the whole frames one row
  spans, raising when the pair gives a fractional row;
- `exact_timings(...)` — every tempo whose row is a whole number of frames at one speed, ordered by row
  length;
- `nearest_timing(target_frames, ...)` — the closest achievable row length, resolving ties to the shorter
  row.

Each format package re-exposes these three bound to its own speed and tempo ranges. The ranges are the
whole difference: at 44100 Hz and speed 1 the shortest whole-frame row Impulse Tracker reaches is 441
frames, while FastTracker 2's sixteen-bit tempo reaches 2.

The same clock read in seconds gives `tick_seconds(tempo)` — the unit envelope breakpoints and note fades
are counted in — `row_seconds(speed, tempo)` for material laid out in time, and `elapsed_ticks(seconds,
tempo)` for the whole tick a duration falls on. A caller fitting material to a whole-frame lattice works
in frames; one placing a breakpoint or a fade works in ticks.

# The domain model

One model describes a piece of tracker music. Each format converts to and from it. The code under
`trackmod/core` handles only musical content, and bytes belong to the formats.

## Song

`trackmod.core.songs.song.Song` is the whole piece:

| Field | Meaning |
|---|---|
| `name` | The module title |
| `channels` | The width of every pattern |
| `patterns` | The grids, indexed by the order list |
| `order` | Which patterns play, and in what sequence |
| `voices` | What the instrument column of a cell refers to |
| `playback` | The clock the song starts on |

Patterns and voices are flat tuples. The order list indexes into the patterns, and the instrument column
indexes into the voices, so a song is self-contained. A validator checks three things. Every pattern has
the song's width. Every entry in the order list points to a pattern that exists. Every value in every
instrument column points to a voice that exists.

`OrderList` holds the playable positions and a `restart` position. Each format handles the separator and
end-of-song markers in its own order table. `Playback` holds `speed`, the number of ticks per row, and
`tempo`, in beats per minute.

## Voices

Every tracker cell has an instrument column. What the number in it refers to depends on the format. Amiga
ProTracker, Soundtracker and Scream Tracker 3 refer to a **sample**. FastTracker 2 refers to an
**instrument**, which routes keys onto samples of its own. Impulse Tracker refers to either and records
which in one header bit. The model expresses this as a union of two tables, one for each way of
addressing:

```python
class SampleVoices(BaseModel):
    samples: tuple[Sample, ...]

class InstrumentVoices(BaseModel):
    instruments: tuple[Instrument, ...]
    samples: tuple[Sample, ...]

Voices = SampleVoices | InstrumentVoices
```

A song holds one table or the other, because a file uses one mode throughout. Both tables answer the same
two questions, so the common code path needs no branches:

- `slots`: how many values the instrument column may refer to;
- `samples`: the waveforms, which is what sizing and serialization ask for.

Under `SampleVoices`, a key plays its waveform at the pitch it was pressed at, so the sample alone decides
what a voice does. Under `InstrumentVoices`, the cell reaches an instrument first. The instrument's keymap
(which sample and note each key plays), envelopes, fadeout, levels and note behaviors shape every voice it
starts.

**Conversion is an explicit call.** `trackmod.core.voices.convert` holds the pair:

```python
raised(sample_voices)         # every sample gains an instrument routing every key to it at its own pitch
flattened(instrument_voices)  # every instrument contributes the one waveform its keys reach
```

`raised` always succeeds. `flattened` refuses an instrument that reaches several samples or plays a key at
another key's pitch, because a table of samples has no room for either. Converting a FastTracker 2 song
into one that a sample-addressed format can write is therefore a step you take on purpose, and it can fail.

Each format writes one kind of table, except Impulse Tracker, which writes either and records the choice
in its header. FastTracker 2 takes `InstrumentVoices`. Amiga ProTracker, Soundtracker and Scream Tracker 3
take `SampleVoices`. A song that holds the other kind is refused with an error that names the mismatch.

## Pattern

`Pattern` is **columnar**. It holds five aligned planes of `numpy.int16`, one per column, each shaped
`(rows, channels)`. The value `EMPTY = -1` marks an absent entry.

```
note  instrument  volume  effect  parameter
```

Separate columns let each column be present or absent on its own. A key-off has a note and no other value.
A mid-pattern tempo change has only an effect. Separate columns also let the packers and the size models
read whole planes at once, so measuring a pattern's packed length takes one vectorized pass.

`Pattern` is frozen. To author one, use `trackmod.core.patterns.builder.PatternBuilder`. It fills the grid
cell by cell and freezes it with `build()`. Besides `place(row, channel, cell)`, it offers
`free_effect_channel(row)`. This returns the lowest channel on a row whose effect column is still free, and
a global effect such as a tempo change belongs there.

`Pattern.widened(channels)` pads a grid with silent channels. Formats that store one channel count for the
whole module need this. A padded channel stays in the file, so `channels` reads back as it was declared.

## Cell

A `Cell` holds the values at one position of a pattern grid:

```python
Cell(note=Note(60), instrument=0, volume=64, effect=Effect(command=1, parameter=6))
```

Each of the four fields can be `None` independently. `instrument` is a **zero-based** index into
`song.voices`, and the kind of voice table decides what it refers to. Every format numbers its own column
from one, and its writer adds the offset. In a stored cell, zero means "keep the voice this channel
already plays".

## Notes

`Note` is a key counted in semitones above C-0, in `0..119`. This is Impulse Tracker's numbering.
FastTracker 2 stores the same key one higher. Scream Tracker 3 stores an octave and a semitone, and counts
octaves from the model's second octave. The two Amiga layouts store the period the pitch sounds at. A
tracker octave is one above the MIDI octave of the same pitch, so tracker C-5 is MIDI 72 and
`Note.from_midi(m) == Note(m - 12)`.

`NoteCommand` covers the note-column entries that act on a playing voice: `OFF`, `CUT` and `FADE`. Their
values continue past the key range, so one integer plane holds either kind, and
`NoteValue = Note | NoteCommand`. Each format decides which of the three it spells.
[`formats/README.md`](../formats/README.md) collects that.

## Volumes

`Cell.volume` holds either a level in `0..64` or a `VolumeCommand`. A `VolumeCommand` is one of the twelve
intents that the volume columns express besides levels, paired with the amount it carries.
`VolumeValue = Volume | VolumeCommand` is the union. The commands continue past the level range in the same
integer, just as the note column's commands continue past the key range.

The amount uses the scale that the format's own column counts in, so a stored column reads back as the
value it holds. [`volume.md`](volume.md) lists the runs (ranges of byte values) that each format divides
its volume byte into, and what each run refuses.

## Samples

`Sample` holds float PCM in `[-1, 1]`, a `rate` in **hertz**, a `BitDepth`, two loops and three levels:

| Field | Meaning |
|---|---|
| `volume` | The level a cell with no volume column plays at |
| `gain` | A fixed multiplier applied on top of the level that plays |
| `panning` | A position on the shared `0..255` scale, or `None` to let the tracker decide |

The rate is recorded in hertz so that one song can serve every format. One format stores the frequency
directly, another stores a transposition of the triggering key, and a third stores the tuning row a sample
plays on. Each writer derives its own encoding. A sample with no frames is a valid placeholder slot.

`gain` is where a format's own limits show. FastTracker 2 fixes `gain` at full and reports anything
quieter. The report tells the caller to put the scaling into the waveform.

`pcm` is shaped `(frames,)` for a mono waveform or `(frames, 2)` for a stereo one, with the left channel
first. Both channels of a stereo waveform share every field above, because no format this library reads gives
them their own loop, volume, panning or rate.

`filename` and `vibrato` hold Impulse Tracker's DOS filename and its sample-level auto-vibrato. A format
with room for neither leaves them at their defaults: an empty name and no vibrato.

## Instruments

`Instrument` is a named routing of keys onto samples. It also holds the envelopes that every voice it
starts follows, a fadeout, a level, a panning, and the new-note and duplicate behaviors.

A `Keymap` has exactly 120 entries, one per key. Each entry is either `None` or a `KeyAssignment`:

```python
KeyAssignment(sample=2, note=Note(60))
```

Separating the **pressed key** from the **sounded note** lets one instrument route keys onto different
samples while every key maps to the same note. `pitched_keymap(sample=…)` makes every key sound at its own
pitch. `routed_keymap({…})` assigns only the keys you list and leaves the rest silent.

`Envelope` is a curve made of breakpoints. Its optional `loop` and `sustain` spans are ranges of point
indices. An instrument that has no envelope of a given kind leaves that property unchanged. That is how an
envelope is switched off.

### Describing a curve in seconds

An envelope stores **ticks**, and the length of a tick follows the tempo, so one curve written for two
clocks is two envelopes. `trackmod.core.envelopes.curve` lets you state a curve in the terms it was
measured in and fits it to a clock:

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

Each breakpoint moves to the tick its time falls on, and each value moves to the scale the format uses. The
resulting ticks always ascend. Two breakpoints that fall inside one tick are moved apart. A curve that
reaches past the last tick the format counts is moved back into the ticks that remain, so the end of the
curve stays represented. `envelope_seconds(envelope, tempo=…)` converts the other way. Use it to compare
what a stored curve does with the trajectory it was fitted to.

Ticks depend on a tempo, so an instrument that travels on its own should be kept beside the tempo its
envelopes were fitted at. An `.iti` or an `.xi` holds a curve and has no clock to read it by.

### Fading a released voice

`fadeout` is a **rate**. A voice being faded has a counter that starts full and drops by the instrument's
fadeout every tick. What remains of the counter scales the level the voice plays at, so the fade lasts
`counter / fadeout` ticks. The size of the counter depends on the format. The shared `fade` functions take
it as a parameter, and each format's own `fade` module supplies it, following the same pattern as
`timing`:

```python
fadeout_value(0.25, counter=1024, tempo=125)   # 82, the rate that fades a voice out in a quarter second
fade_seconds(82, counter=1024, tempo=125)      # 0.2498…, the same number read the other way
```

Impulse Tracker's counter is 1024. FastTracker 2 counts down from 32768, so the same quarter second is a
fadeout of 2621 there.

`NO_FADEOUT` keeps the counter full. The voice then keeps its level for as long as it sounds, which reads
as a fade of unbounded length. `fadeout_value` raises for a fade slower than a counter step of one, because
zero stands for a fade of unbounded length. **When** the fade begins is set by each format's own
convention, described in the format documents.

## Moving an instrument between songs

A keymap points to positions in the sample table of the song it belongs to, so an instrument on its own is
half a voice. `trackmod.core.instruments.unit.InstrumentUnit` holds the other half: the samples its keys
reach, numbered from zero. `trackmod.core.instruments.transfer` moves units in and out of songs:

```python
unit = extract(song.voices, 0)     # the instrument and the waveforms it sounds
held = units(song.voices)          # the same, for every instrument the table numbers
voices = combine([unit, other])    # one table, each keymap restated against the samples behind it
```

`combine` returns exactly the `voices=` table that `Song` takes. `extract` and `combine` work on
`InstrumentVoices`. `units` accepts either kind of table and first raises a sample table onto instruments,
because a voice that a cell names directly is a plain sample and travels as one.
`Instrument.rerouted(positions)` does the renumbering. It changes the routing and leaves every envelope, level
and behavior unchanged, so an instrument lifted out of one module and written into another sounds as it did
before.

Each unit keeps its own copy of a waveform that another unit also holds. Impulse Tracker stores the
resulting table as it is. FastTracker 2 gives every instrument its own copies in any case (see
[`formats/README.md`](../formats/README.md)).

A unit is also what a format stores as a standalone file, an `.iti` or an `.xi`:

```python
unit = ITInstrumentFile.load(Path("piano.iti")).unit    # one voice, ready to graft
XMInstrumentFile.from_unit(unit, compliance=Compliance.CANONICAL).save(Path("piano.xi"))
```

`InstrumentFile` is the protocol that both instrument-file classes follow. It is the counterpart of
`TrackerModule` for a container that holds one voice. Each file follows the limits of its format, so an
instrument can carry the same values in either container.

If you have bytes and the extension they were saved under, one call in `trackmod.trackers.registry` returns
the same voices, whichever format wrote them:

```python
voices = parse_voices(data, extension=".iti")   # one voice, from a standalone instrument
voices = parse_voices(data, extension=".it")    # every voice a module numbers
```

The result says which kind of table it is, so the type of container no longer matters once the bytes are
read. `MODULE_EXTENSIONS` and `INSTRUMENT_EXTENSIONS` list which suffix belongs to which kind of file, in
either capitalization. A consumer can use them to accept whichever container a producer ships.

## Reading files with out-of-range values

The model above describes a **well-formed** song, which is what this library writes. Files written by real
trackers sometimes hold values outside that model. Examples are an envelope loop that ends before it
begins, a sample loop that reaches past the waveform, and an order that points to a pattern the file leaves
out. Refusing these files would refuse most of the modules that exist.

So a parser moves each value back into range and reports it. `Repairs` collects what one parse did, counts
repeats of one repair on one subject once, and reports everything as a single `RepairWarning`:

```
RepairWarning: values drawn into range as the file was read: sample 3: rate 0 read as 8363 Hz;
song: 2 order positions naming no stored pattern dropped
```

Each format's document lists the values it repairs, in the section that reads them.
[`architecture.md`](../contributing/architecture.md) describes the rule that the three mechanisms follow.
A bound reports a quantity, a `ValueError` refuses content with no encoding, and a repair reads a file as
it stands.

## Timing

Every format here shares one clock. A tick lasts `5 / (2 * tempo)` seconds and a row lasts `speed` ticks,
so a row spans this many frames:

```
speed * 5 * frame_rate / (2 * tempo)
```

`trackmod.core.timing.lattice` works with that exact rational. This matters when a caller derives a block
length from the row it is fitting material to. The module provides three functions:

- `row_frames(speed, tempo, frame_rate=…, speed_bound=…, tempo_bound=…)`: the whole frames one row spans.
  It raises when the pair gives a fractional row.
- `exact_timings(...)`: every tempo whose row is a whole number of frames at one speed, ordered by row
  length.
- `nearest_timing(target_frames, ...)`: the closest achievable row length. Ties resolve to the shorter
  row.

Each format package defines one `TIMINGS` object that holds its own speed and tempo ranges, and the three
functions take their ranges from it. The ranges are the whole difference between formats. At 44100 Hz and
speed 1, the shortest whole-frame row in Impulse Tracker is 441 frames. Every format here with a one-byte
tempo shares that floor. FastTracker 2 has a sixteen-bit tempo, and its shortest row is 2 frames.

The same clock measured in seconds gives three more functions:

- `tick_seconds(tempo)`: the length of a tick, which is the unit that envelope breakpoints and note fades
  are counted in;
- `row_seconds(speed, tempo)`: the length of a row, for material laid out in time;
- `elapsed_ticks(seconds, tempo)`: the whole tick that a duration falls on.

Work in frames when fitting material to a whole-frame lattice. Work in ticks when placing a breakpoint or a
fade.

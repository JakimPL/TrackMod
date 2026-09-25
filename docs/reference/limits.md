# Limits and compliance

A tracker format has three ceilings, and they are usually different. The first is what the format's own
tracker accepted in its editor. The second is what the players that came after it can read, which a module
needs in order to play at all. The third is what the record layout can physically hold. A value past that
third ceiling has no bytes to sit in. For example, FastTracker 2 edits patterns of 256 rows, the players
descended from it read 1024, and the pattern header stores the row count in sixteen bits. `trackmod`
records all three ceilings, so a caller can choose one deliberately and a reader can tell which one a file
needed.

## The types

```python
class Capability(StrEnum): CHANNELS, PATTERNS, ORDERS, PATTERN_ROWS, PATTERN_BYTES, INSTRUMENTS, ...
class Compliance(StrEnum): CANONICAL, EXTENDED, STRUCTURAL

class Bound(BaseModel):      minimum: int; maximum: int
class Capacity(BaseModel):   canonical: Bound; extended: Bound; structural: Bound
class Tier(BaseModel):       level: Compliance; bound: Bound
class Limits(BaseModel):     compliance: Compliance; capacities: Mapping[Capability, Capacity]
class Violation(BaseModel):  capability; value; bound; level; subject
class LimitError(ValueError): violations: tuple[Violation, ...]
```

One enum names the three levels. A violation records which level it broke, so the level a caller writes to
and the level a value went past use the same three names throughout.

`Capability` is the shared vocabulary. It has one name per quantity, and every format uses the same name,
so a caller asks "how many channels may I use?" the same way for every format.

Each format declares one `Capacity` per capability in its `spec/capacities.py`. A `Capacity` holds three
bounds, from the tightest to the widest. Each bound contains the one before it, so a table that lists them
out of order fails where it is written. `Capacity.fixed(bound)` describes a field with no headroom, where
all three bounds are the same.

`Limits` reads that table at one compliance level and answers two different questions:

- `limits.bound(capability)`: what a caller **may use**, which is the bound at that level;
- `limits.check(capability, value, subject=…)`: how a value the caller already has **grades**.

## How a value is graded

A value is graded by the **widest ceiling it goes past**. Going past a wide bound means going past every
tighter one, and the widest ceiling tells who can still read the file back. That ceiling becomes the
violation's `level`:

- `CANONICAL` for a value that only the format's own tracker refuses;
- `EXTENDED` for a value that the players descended from that tracker refuse too;
- `STRUCTURAL` for a value that the bytes cannot hold at all.

A violation is reported when its level is the level the module is held to, or a wider one. A structural
violation is therefore reported at every level. A module held to a wider level still gets validation, and
the validation uses the wider bound.

| Value | at `CANONICAL` | at `EXTENDED` | at `STRUCTURAL` |
|---|---|---|---|
| Inside every bound | — | — | — |
| Past the tracker's own | `CANONICAL` | — | — |
| Past what the players read | `EXTENDED` | `EXTENDED` | — |
| Past what the layout holds | `STRUCTURAL` | `STRUCTURAL` | `STRUCTURAL` |

## Collecting every violation

`Module.violations()` checks the whole song and returns every violation it finds, so a caller sees all of
its problems at once. `to_bytes()` calls `require(...)`, which raises a `LimitError` that holds the full
tuple.

```python
module = XMModule.from_song(song, compliance=Compliance.CANONICAL)
for violation in module.violations():
    print(violation)     # song: tempo is 441, outside 32..255 (canonical)
```

## Which ceilings a file needs

The levels above are what a caller **writes** to. Reading asks the opposite question: which ceilings did an
existing file need? Every module and instrument file can answer it.

```python
module = ITModule.load(Path("song.it"))

module.reach                 # Compliance.EXTENDED
module.exceeded()            # song: channels is 96, outside 1..64 (canonical)
module.require_reach(Compliance.CANONICAL)      # raises LimitError
```

`reach` is the strictest level that the song fits inside:

- `CANONICAL`: the module opens in the tracker its format names.
- `EXTENDED`: the module needs a player descended from that tracker.
- `STRUCTURAL`: the module's values are stored, but no player reads them faithfully. The tracker scene
  calls this a hacked module.

A song that holds a value no record layout can store fits none of the three, and `reach` is `None`. That
result tells it apart from a song that the widest level does hold. `exceeded()` gives the detail behind
`reach`. It grades at the strictest level, whatever level the module is held to. `require_reach` refuses a
module that goes further than the caller accepts.

A module read from a file is held to `STRUCTURAL`, because a file that exists proves its values were
storable. So `violations()` is empty for a file that a later tracker wrote, and the reach is a separate
question.

## Limit errors and unsupported content

The limits system grades **quantities**. A value outside a `Bound` becomes a `Violation`. `to_bytes`
collects every violation and raises one `LimitError`.

Some content has no encoding in a format at all. That content is not a quantity, so no bound exists to
report it against. It raises `ValueError` at the point where the writer meets it. The main cases are:

- FastTracker 2 has many of them: a note cut or fade in the note column (it stores only a key off), a
  sustain loop, a pitch envelope, an envelope that sustains over a span of points, and a keymap that
  transposes one key of a sample differently from another.
- The two Amiga layouts refuse a volume column, a note command of any kind, a stereo or sixteen-bit
  waveform, and a per-sample panning. Soundtracker adds one more of its own. Its header holds where a song
  starts and has no field for where it resumes, so a song that resumes past its first position raises.
- Scream Tracker 3 stores a note cut as its only note command and pans by channel, not by sample. It meets
  two of its refusals while reading: a record that holds an OPL patch, and a waveform stored in the ADPCM
  that a later tracker wrote.

The volume column is another place where this line falls, for the three formats that have one. Between
them, the volume columns express twelve intents. Impulse Tracker has nine of them, FastTracker 2 ten and
Scream Tracker 3 one. So each of these raises: a pitch slide written as FastTracker 2, a vibrato speed
written as Impulse Tracker, and a slide of any kind written as Scream Tracker 3 (see
[`volume.md`](volume.md)). Every `to_bytes` documents both error paths in its `Raises:` clause.

`Module.violations()` grades only quantities, so content with no encoding in the format surfaces at
`to_bytes()`.

The two errors call for different fixes. A `LimitError` means *use a smaller number*. A `ValueError` means
*this idea has no home in this format, so express it another way*.

## The table

The table has one column per format and one row per capability. Three bounds separated by `/` are
canonical, extended and structural, in that order. A single bound applies at every level, because the field
has no headroom.

| Capability | Impulse Tracker | FastTracker 2 | Amiga ProTracker | Scream Tracker 3 | Soundtracker |
|---|---|---|---|---|---|
| `channels` | 1..64 / 1..127 / 1..127 | 1..32 / 1..127 / 1..65535 | 4..4 / 1..32 / 1..99 | 1..16 / 1..32 / 1..32 | 4..4 |
| `patterns` | 0..200 / 0..240 / 0..254 | 0..256 / 0..256 / 0..65535 | 0..64 / 0..256 / 0..256 | 0..100 / 0..254 / 0..254 | 0..256 |
| `orders` | 0..256 / 0..65535 / 0..65535 | 0..256 / 0..256 / 0..65535 | 0..128 | 0..255 / 0..65535 / 0..65535 | 0..128 |
| `pattern_rows` | 32..200 / 1..1024 / 1..65535 | 1..256 / 1..1024 / 1..65535 | 64..64 | 64..64 | 64..64 |
| `pattern_bytes` | 0..65535 | 0..65535 | — | 0..65535 | — |
| `block_offset` | — | — | — | 0..1048560 | — |
| `instruments` | 0..99 / 0..255 / 0..255 | 0..128 / 0..255 / 0..255 | — | — | — |
| `samples` | 0..99 / 0..255 / 0..255 | 0..2048 / 0..65025 / 0..65025 | 0..31 | 0..99 / 0..255 / 0..255 | 0..15 |
| `samples_per_instrument` | 0..255 | 0..16 / 0..255 / 0..255 | — | — | — |
| `sample_frames` | 0..4294967295 | 0..4294967295 | 0..131070 | 0..64000 / 0..4294967295 / 0..4294967295 | 0..131070 |
| `sample_bytes` | — | 0..4294967295 | 0..131070 | 0..64000 / 0..17179869180 / 0..17179869180 | 0..131070 |
| `sample_offset` | — | — | — | 0..268435440 | — |
| `sample_rate` | 1..9999999 / 1..4294967295 / 1..4294967295 | 10..25662141 | 7893..8795 | 1..65535 / 1..4294967295 / 1..4294967295 | 7893..8795 |
| `sample_volume` | 0..64 | 0..64 | 0..64 | 0..64 | 0..64 |
| `sample_gain` | 0..64 | 64..64 | 64..64 | 64..64 | 64..64 |
| `instrument_volume` | 0..128 | 128..128 | — | — | — |
| `envelope_points` | 1..25 | 1..12 | — | — | — |
| `envelope_value` | -128..127 | 0..64 | — | — | — |
| `envelope_tick` | 0..65535 | 0..65535 | — | — | — |
| `fadeout` | 0..128 / 0..65535 / 0..65535 | 0..4095 / 0..65535 / 0..65535 | — | — | — |
| `note` | 0..119 | 0..95 | 48..83 / 21..119 / 21..119 | 12..107 / 12..119 / 12..119 | 48..83 / 21..119 / 21..119 |
| `tempo` | 32..255 | 32..255 / 32..1000 / 1..65535 | 125..125 | 32..255 | 125..125 |
| `speed` | 1..255 | 1..31 / 1..65535 / 1..65535 | 6..6 | 1..255 | 6..6 |
| `volume_command` | 0..9 | 0..15 | — | — | — |
| `volume_panning` | 0..64 | 0..15 | — | 0..64 | — |
| `song_volume` | 0..128 / 0..128 / 0..255 | — | — | 0..64 / 0..64 / 0..255 | — |
| `mix_volume` | 0..128 / 0..128 / 0..255 | — | — | 0..127 | — |
| `message_bytes` | 0..8000 / 0..65535 / 0..65535 | — | — | — | — |

A dash means the format has no such field. The format declares no capacity for it, so `limits.bound(...)`
and `limits.check(...)` both refuse it by name. Call `limits.declares(...)` first to find out. The dashes
follow from these facts:

- FastTracker 2 has no song-wide volume, no mix volume and no song message.
- Scream Tracker 3 keeps one table of samples, so it has neither instrument records nor envelopes.
- The two Amiga formats have none of those, and no volume column either.
- Impulse Tracker records a waveform's length in frames, so `sample_bytes` is the one row it leaves empty
  while the other four formats fill it.

Asking about a dash is asking about a field that does not exist. That is a different mistake from asking
for a value out of range.

Soundtracker gives a single bound in every row it fills except one. Its header holds no channel count, no
clock and no pattern height, so these are fixed at the four channels its machine played and the clock it
opened on. The one row with headroom is `note`: the twelve bits of the period field reach further than the
three octaves that its own trackers tabulated.

The two offset rows show how far a format's own pointers reach. Scream Tracker 3 finds every block by the
paragraph it opens on. A two-byte entry reaches 1048560 bytes into a file. An instrument record uses a
third byte for its waveform pointer, which reaches 268435440. The other four formats walk their files front
to back and locate nothing by address, so no distance limits them. A module that packs more patterns than
the two-byte table reaches gets that reported as a quantity. A writer would otherwise meet it as an
overflow.

`sample_frames` and `sample_bytes` measure one waveform in two ways. `sample_frames` counts the frames per
channel. `sample_bytes` counts the block those frames occupy once the bit depth and the channel count are
included. The two are equal for an eight-bit mono waveform and differ for every other kind. That is why
Scream Tracker 3's loader ceiling of 64000 **bytes** belongs in the row that counts bytes. For example, a
sixteen-bit stereo sample of 20000 frames is well inside the frame ceiling but comes to 80000 bytes, and
the violation reports that number.

`volume_command` is the one row that cannot be compared across formats. Its numbers show how far an amount
reaches inside a run. The two formats that have this row support different sets of intents, so a song that
fits in the amount can still be refused for its intent. [`volume.md`](volume.md) lists all twelve intents
side by side.

A capacity pinned to a single value means the format applies no such adjustment. `sample_gain` at 64 means
FastTracker 2 multiplies nothing. Amiga ProTracker's `speed` and `tempo` at 6 and 125 mean its header holds
no clock, so a song that asks to start on another clock gets a violation. The two formats of that lineage
pin `pattern_rows` at 64, the height of every pattern they store.

## Where each bound comes from

Each level comes from a different source. That difference is why the three are kept apart.

- **Canonical** is the ceiling of the tracker's own editor: 200 patterns and 99 samples in Impulse Tracker,
  32 channels in FastTracker 2, sixteen channels in Scream Tracker 3, and four in Amiga ProTracker.
- **Structural** is read off the record layout, so it can be proven:
  - a sixteen-bit field holds 65535;
  - a packed cell announces its channel as `(channel + 1) | 0x80`, which leaves seven bits for the number;
  - a twelve-bit period can express keys down to 21, and none below;
  - a channel settings table of 32 entries names 32 channels;
  - four tag characters that spell two decimal digits name up to 99 channels;
  - an order byte keeps `0xFE` and `0xFF` for the separator and the end of song, so it names `0..253`.
- **Extended** is measured. It tests which values the players descended from these trackers read back
  faithfully.

The levels differ in 34 of the 93 entries that the five formats' capacity tables hold between them. These
are the ones worth naming:

| Bound | canonical | extended | structural |
|---|---|---|---|
| IT pattern rows | 200, the editor's limit | 1024, past which the file is refused | 65535, the header's sixteen-bit field |
| XM pattern rows | 256, the editor's limit | 1024, past which the height is moved back into range | 65535, the header's sixteen-bit field |
| XM channels | 32, the editor's limit | 127, past which the file is refused | 65535, the header's sixteen-bit field |
| XM tempo | 255, what one byte holds | 1000, past which the tempo is moved back into range | 65535, the header's sixteen-bit field |
| IT patterns | 200, the editor's limit | 240, past which the count is moved back into range | 254, what an order byte can name |
| MOD, ST note range | 48..83, the three tabulated octaves | 21..119, every period the field holds | the same |
| MOD channels | 4, the only width the tracker wrote | 32, as far as the players read | 99, as far as two digits spell |
| MOD patterns | 64, what the plain tag was read with | 256, what an order byte can name | the same |
| IT sample rate | 9999999, the editor's limit | 4294967295, the record's four bytes | the same |
| IT, S3M song volume | 128 and 64, each tracker's limit | the same | 255, the byte that carries it |
| XM patterns, orders | 256 each, the editor's limit | the same | 65535, the header's sixteen-bit fields |
| S3M channels | 16, the slots the tracker mixes | 32, the settings table's entries | the same |
| S3M sample frames | 64000, the loader's ceiling at one byte per frame | 4294967295, the record's own field | the same |
| S3M sample bytes | 64000, what the tracker's loader holds | that field at four bytes per frame | the same |
| S3M sample rate | 65535, the low sixteen bits the tracker reads | 4294967295, the whole field | the same |
| S3M note range | 12..107, the eight octaves it names | 12..119, every key two nibbles can spell | the same |

The Impulse Tracker tempo stays at **255 at every level**, as do the remaining 59 entries, and it is the
one of them a caller is most likely to run into. Its header tempo is a single byte at offset 51. A tempo of
441 cannot be written at all, and it does not wrap around into a slower song. Reporting it as a
`STRUCTURAL` violation gives a clear message. Without that report, the caller would see a `struct.error`
from deep inside a writer.

The effect column has its own bound, because it is a separate field from the header. FastTracker 2's `Fxx`
has one parameter byte, so a **mid-song** tempo change can be at most 255, even in a module whose header
holds 441. `XM_EFFECTS.set_tempo(441)` raises, and the header still holds 441.

## Choosing a level

- `Compliance.CANONICAL` is the level to write for a module that has to open in the tracker it names.
- `Compliance.EXTENDED` is the level for a module that has to play in OpenMPT, in libopenmpt, or in
  anything descended from them.
- `Compliance.STRUCTURAL` is the level for a module that has to be stored. Reading holds a file to this
  level.

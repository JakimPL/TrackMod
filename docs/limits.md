# Limits and compliance

A tracker format has three ceilings, and they are rarely the same one. There is what the tracker the
format was written for honoured in its own editor. There is what the players that came after it read,
which is what a module needs in order to play at all. And there is what the record layout physically
holds, past which a value has no bytes to sit in. FastTracker 2 edits patterns of 256 rows, the players
descended from it read 1024, and the pattern header states the count in sixteen bits. `trackmod` states
all three, so a caller can choose a ceiling deliberately and a reader can say which one a file needed.

## The pieces

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

One enum names the three levels, and a violation states which of them it broke, so the level a caller
writes to and the level a value passed are the same three words throughout.

`Capability` is the shared vocabulary: one name per quantity, stated the same way by every format, so a
caller asking "how many channels may I use?" phrases the question once.

Each format declares a `Capacity` per capability in its `spec/capacities.py`, holding the three bounds
from the tightest to the widest. Each contains the one before it, so a table that states them out of
order fails where it is written. A `Capacity.fixed(bound)` is a field with no headroom anywhere, where
all three coincide.

`Limits` reads that table at one compliance level and answers two different questions:

- `limits.bound(capability)` — what a caller **may use**, which is that level's bound;
- `limits.check(capability, value, subject=…)` — how a value it already has **grades**.

## How a value grades

A value is graded against the **widest ceiling it passes**, because passing a wide bound means passing
every tighter one, and the widest is what says who will still read the file back. That ceiling becomes
the violation's `level`: `CANONICAL` for a value only the format's own tracker refuses, `EXTENDED` for
one the players descended from it refuse too, and `STRUCTURAL` for one the bytes cannot hold at all.

A violation is reported when its ceiling is the level the module is held to, or a wider one. So a
structural violation is reported at every level, and a module held to a wider level is not one that
skips validation — it is one validated against a wider bound.

| Value | at `CANONICAL` | at `EXTENDED` | at `STRUCTURAL` |
|---|---|---|---|
| Inside every bound | — | — | — |
| Past the tracker's own | `CANONICAL` | — | — |
| Past what the players read | `EXTENDED` | `EXTENDED` | — |
| Past what the layout holds | `STRUCTURAL` | `STRUCTURAL` | `STRUCTURAL` |

## Reporting, not raising one at a time

`Module.violations()` walks the whole song and returns every violation it found, so a caller sees all of
its problems at once. `to_bytes()` calls `require(...)`, which raises `LimitError` carrying the full
tuple.

```python
module = XMModule.from_song(song, compliance=Compliance.CANONICAL)
for violation in module.violations():
    print(violation)     # song: tempo is 441, outside 32..255 (canonical)
```

## What a file reaches past

The levels above are what a caller **writes** to. Reading asks the other way round: given a file that
already exists, which ceilings did it need? Every module and instrument file answers that.

```python
module = ITModule.load(Path("song.it"))

module.reach                 # Compliance.EXTENDED
module.exceeded()            # song: channels is 96, outside 1..64 (canonical)
module.require_reach(Compliance.CANONICAL)      # raises LimitError
```

`reach` is the strictest level the song fits inside: `CANONICAL` for a module that opens in the tracker
its format names, `EXTENDED` for one that needs a player descended from it, and `STRUCTURAL` for one
whose values are stored but read faithfully by nothing — what a tracker scene would call a hacked
module. A song carrying a value no record layout holds fits none of the three, and `reach` is `None`
there, which is the answer that separates it from a song the widest level does hold. `exceeded()` is the
detail behind it, graded at the strictest level whatever level the module is held to, and `require_reach`
refuses a module that goes further than a caller will accept.

Reading holds a module to `STRUCTURAL`, because a file that exists is evidence its values were storable,
so `violations()` stays empty for one a later tracker wrote and the reaching is asked for separately.

## What a format refuses versus what it cannot express

The limits system grades **quantities**. A value outside a `Bound` becomes a `Violation`, and `to_bytes`
raises `LimitError` after collecting every one of them.

Content a format has no encoding for at all is not a quantity. There is no bound to report it against,
so it raises `ValueError` where it is met. FastTracker 2 is where much of this line falls: a note cut or
fade in the note column (it stores a key off and nothing else), a sustain loop, a pitch envelope, an
envelope sustaining over a span of points, and a keymap that transposes one key of a sample differently
from another. Amiga ProTracker adds its own: a volume column, a note command of any kind, a stereo or
sixteen-bit waveform, and a per-sample panning. Scream Tracker 3 stores a note cut and no other command,
pans by channel rather than by sample, and meets two of its refusals while reading — a record holding an
OPL patch, and a waveform stored in the ADPCM a later tracker wrote.

The volume column is where the line falls for the three that carry one: Impulse Tracker names nine of the
twelve intents the columns state between them, FastTracker 2 ten and Scream Tracker 3 one, so a pitch
slide written as FastTracker 2, a vibrato speed written as Impulse Tracker and a slide of any kind written
as Scream Tracker 3 each raise (see [`volume.md`](volume.md)). Every `to_bytes` documents the two paths in
its `Raises:` clause.

The distinction is worth keeping because the two call for different fixes. A `LimitError` says *use a
smaller number*; a `ValueError` says *this idea has no home in this format, express it another way*.

## The table

One column per format, and one row per capability. Three bounds separated by `/` are canonical, extended
and structural; a single bound is a field with no headroom at any level.

| Capability | Impulse Tracker | FastTracker 2 | Amiga ProTracker | Scream Tracker 3 |
|---|---|---|---|---|
| `channels` | 1..64 / 1..127 / 1..127 | 1..32 / 1..127 / 1..65535 | 4..4 / 1..32 / 1..99 | 1..16 / 1..32 / 1..32 |
| `patterns` | 0..200 / 0..240 / 0..254 | 0..256 / 0..256 / 0..65535 | 0..64 / 0..256 / 0..256 | 0..100 / 0..254 / 0..254 |
| `orders` | 0..256 / 0..65535 / 0..65535 | 0..256 / 0..256 / 0..65535 | 0..128 | 0..255 / 0..65535 / 0..65535 |
| `pattern_rows` | 32..200 / 1..1024 / 1..65535 | 1..256 / 1..1024 / 1..65535 | 64..64 | 64..64 |
| `pattern_bytes` | 0..65535 | 0..65535 | — | 0..65535 |
| `block_offset` | — | — | — | 0..1048560 |
| `instruments` | 0..99 / 0..255 / 0..255 | 0..128 / 0..255 / 0..255 | — | — |
| `samples` | 0..99 / 0..255 / 0..255 | 0..2048 / 0..65025 / 0..65025 | 0..31 | 0..99 / 0..255 / 0..255 |
| `samples_per_instrument` | 0..255 | 0..16 / 0..255 / 0..255 | — | — |
| `sample_frames` | 0..4294967295 | 0..4294967295 | 0..131070 | 0..64000 / 0..4294967295 / 0..4294967295 |
| `sample_bytes` | — | 0..4294967295 | 0..131070 | 0..64000 / 0..17179869180 / 0..17179869180 |
| `sample_offset` | — | — | — | 0..268435440 |
| `sample_rate` | 1..9999999 / 1..4294967295 / 1..4294967295 | 10..25662141 | 7893..8795 | 1..65535 / 1..4294967295 / 1..4294967295 |
| `sample_volume` | 0..64 | 0..64 | 0..64 | 0..64 |
| `sample_gain` | 0..64 | 64..64 | 64..64 | 64..64 |
| `instrument_volume` | 0..128 | 128..128 | — | — |
| `envelope_points` | 1..25 | 1..12 | — | — |
| `envelope_value` | -128..127 | 0..64 | — | — |
| `envelope_tick` | 0..65535 | 0..65535 | — | — |
| `fadeout` | 0..128 / 0..65535 / 0..65535 | 0..4095 / 0..65535 / 0..65535 | — | — |
| `note` | 0..119 | 0..95 | 48..83 / 21..119 / 21..119 | 12..107 / 12..119 / 12..119 |
| `tempo` | 32..255 | 32..255 / 32..1000 / 1..65535 | 125..125 | 32..255 |
| `speed` | 1..255 | 1..31 / 1..65535 / 1..65535 | 6..6 | 1..255 |
| `volume_command` | 0..9 | 0..15 | — | — |
| `volume_panning` | 0..64 | 0..15 | — | 0..64 |
| `song_volume` | 0..128 / 0..128 / 0..255 | — | — | 0..64 / 0..64 / 0..255 |
| `mix_volume` | 0..128 / 0..128 / 0..255 | — | — | 0..127 |
| `message_bytes` | 0..8000 / 0..65535 / 0..65535 | — | — | — |

A dash means the format keeps no such field, so it states no capacity and `limits.bound(...)` and
`limits.check(...)` both refuse it by name; `limits.declares(...)` is the question to ask first.
FastTracker 2 has no song-wide volume, no mix volume and no song message; Scream Tracker 3 keeps one
table of samples, so it has neither instrument records nor envelopes; Amiga ProTracker keeps none of
those and no volume column either. Impulse Tracker states a waveform's length in frames, which is why
`sample_bytes` is the one row it leaves empty and the other three fill. A caller reaching for a dash is
asking about a field that does not exist, which is a different mistake from asking for a value out of
range.

The two offsets are the reach of a format's own pointers: Scream Tracker 3 finds every block by the
paragraph it opens on, so a two-byte entry sees 1048560 bytes into a file and the third byte an
instrument record spends on its waveform sees 268435440. The other three walk their files front to back
and address nothing, so no distance bounds them. A module packing more patterns than the two-byte table
reaches is told so as a quantity, where a writer would otherwise meet it as an overflow.

`sample_frames` and `sample_bytes` measure one waveform two ways: the frames it holds per channel, and
the block those frames come to once the depth and the channel count are counted in. The two coincide for
an eight-bit mono waveform and part company for every other, which is what puts Scream Tracker 3's
loader ceiling of 64000 **bytes** in the row that is denominated in them: a sixteen-bit stereo sample of
20000 frames sits well inside the frame ceiling, comes to 80000 bytes, and that is the number reported.

A capacity pinned to a single value states that the format applies no such adjustment: `sample_gain` at
64 says FastTracker 2 multiplies nothing, and Amiga ProTracker's `speed` and `tempo` at 6 and 125 say
its header states no clock, so a song asking to start on another is told rather than losing it. The two
formats of that lineage pin `pattern_rows` at 64, which is the height every pattern they store has.

## Where each bound comes from

Each level is established a different way, and the difference is what makes the three worth keeping
apart.

**Canonical** is the tracker's own editing ceiling — 200 patterns and 99 samples in Impulse Tracker, 32
channels in FastTracker 2, sixteen in Scream Tracker 3, four in Amiga ProTracker. **Structural** is read
off the record layout and is provable: a sixteen-bit field holds 65535, a packed cell announcing its
channel as `(channel + 1) | 0x80` leaves seven bits for the number, a twelve-bit period reaches down to
one key and no further, a channel settings table of 32 entries names 32 channels, four tag characters
spelling two decimal digits name up to 99, and an order byte whose `0xFE` and `0xFF` are the separator
and the end of song names `0..253`. **Extended** is measured, by asking the players descended from these
trackers what they read back rather than what they merely accept.

The cases where the levels part company are the ones worth naming:

| Bound | canonical | extended | structural |
|---|---|---|---|
| IT pattern rows | 200, the editor's own | 1024, past which the file is refused | 65535, the header's word |
| XM pattern rows | 256, the editor's own | 1024, past which the height is drawn back | 65535, the header's word |
| XM channels | 32, the editor's own | 127, past which the file is refused | 65535, the header's word |
| XM tempo | 255, one byte of it | 1000, past which the tempo is drawn back | 65535, the header's word |
| IT patterns | 200, the editor's own | 240, past which the count is drawn back | 254, what an order byte names |
| MOD note range | 48..83, the three tabulated octaves | 21..119, every period the field holds | the same |
| MOD channels | 4, the only width the tracker wrote | 32, as far as the players read | 99, as far as two digits spell |
| MOD patterns | 64, what the plain tag was read with | 256, what an order byte names | the same |
| IT sample rate | 9999999, the editor's own | 4294967295, the record's four bytes | the same |
| IT, S3M song volume | 128 and 64, each tracker's own | the same | 255, the byte that carries it |
| XM patterns, orders | 256 each, the editor's own | the same | 65535, the header's words |
| S3M channels | 16, the slots the tracker mixes | 32, the settings table's entries | the same |
| S3M sample frames | 64000, the loader's ceiling at a byte a frame | 4294967295, the record's own field | the same |
| S3M sample bytes | 64000, what the tracker's loader holds | that field at four bytes a frame | the same |
| S3M sample rate | 65535, the low word the tracker reads | 4294967295, the whole field | the same |
| S3M note range | 12..107, the eight octaves it names | 12..119, every key two nibbles spell | the same |

The Impulse Tracker tempo stays at **255 at every level**, and this is the one place the distinction
earns its keep by refusing something. Its header tempo is a single byte at offset 51. A tempo of 441 does
not overflow into a slower song — it cannot be written at all. Reporting it as a `STRUCTURAL` violation
is the difference between a clear message and a `struct.error` from deep inside a writer.

The effect column is bounded separately from the header, because it is a separate field. FastTracker 2's
`Fxx` carries one parameter byte, so a **mid-song** tempo change tops out at 255 even in a module whose
header carries 441. `XM_EFFECTS.set_tempo(441)` raises; the header still holds it.

## Choosing a level

`Compliance.CANONICAL` is the level to write for a module that has to open in the tracker it names.
`Compliance.EXTENDED` is the level for a module that has to play — in OpenMPT, in libopenmpt, in anything
descended from them. `Compliance.STRUCTURAL` is the level for a module that has to be stored, and is
what reading holds a file to.

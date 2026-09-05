# Limits and compliance

A tracker format has two ceilings, and they are rarely the same one. There is what the file's fields can
physically hold, which follows from the record layout, and there is what the tracker the format was
written for actually honoured. FastTracker 2 stores its tempo in sixteen bits and reads eight of them.
That gap is not a curiosity: it is room, and a module written into it plays in the players descended from
those trackers. `trackmod` makes the gap explicit so a caller can use it deliberately.

## The pieces

```python
class Capability(StrEnum): CHANNELS, PATTERNS, ORDERS, PATTERN_ROWS, PATTERN_BYTES, INSTRUMENTS, ...
class Compliance(StrEnum): CANONICAL, EXTENDED
class Severity(StrEnum):   STRUCTURAL, COMPLIANCE

class Bound(BaseModel):      minimum: int; maximum: int
class Capacity(BaseModel):   canonical: Bound; structural: Bound
class Limits(BaseModel):     compliance: Compliance; capacities: Mapping[Capability, Capacity]
class Violation(BaseModel):  capability; value; bound; severity; subject
class LimitError(ValueError): violations: tuple[Violation, ...]
```

`Capability` is the shared vocabulary: one name per quantity, stated the same way by every format, so a
caller asking "how many channels may I use?" phrases the question once.

Each format declares a `Capacity` per capability in its `spec/capacities.py`. `structural` is what the
bytes hold; `canonical` is what the original tracker honours. A `Capacity.fixed(bound)` is a field with
no headroom at all, where the two coincide.

`Limits` reads that table at one compliance level and answers two different questions:

- `limits.bound(capability)` — what a caller **may use**, which is the canonical bound under
  `CANONICAL` and the structural bound under `EXTENDED`;
- `limits.check(capability, value, subject=…)` — how a value it already has **grades**.

A value the layout cannot hold is a `STRUCTURAL` violation and is reported at every compliance level. A
value the layout holds but the tracker ignores is a `COMPLIANCE` violation, reported only under
`CANONICAL`. That single rule is the whole mechanism: an extended module is not one that skips
validation, it is one validated against the wider of the two bounds.

## Reporting, not raising one at a time

`Module.violations()` walks the whole song and returns every violation it found, so a caller sees all of
its problems at once. `to_bytes()` calls `require(...)`, which raises
`LimitError` carrying the full tuple.

```python
module = XMModule.from_song(song, compliance=Compliance.CANONICAL)
for violation in module.violations():
    print(violation)     # song: tempo is 441, outside 32..255 (compliance)
```

## What a format refuses versus what it cannot express

The limits system grades **quantities**. A value outside a `Bound` becomes a `Violation`, and `to_bytes`
raises `LimitError` after collecting every one of them.

Content a format has no encoding for at all is not a quantity. There is no bound to report it against,
so it raises `ValueError` where it is met. FastTracker 2 is where most of this line falls: a note cut or
fade in the note column (it stores a key off and nothing else), a sustain loop, a pitch envelope, an
envelope sustaining over a span of points rather than one point, and a keymap that transposes one key of
a sample differently from another. The volume column is where it falls for both: Impulse Tracker names
nine of the twelve intents the two state between them and FastTracker 2 ten, so a pitch slide written as
FastTracker 2 and a vibrato speed written as Impulse Tracker each raise (see [`volume.md`](volume.md)).
Both `to_bytes` methods document the two paths in their `Raises:` clauses.

The distinction is worth keeping because the two call for different fixes. A `LimitError` says *use a
smaller number*; a `ValueError` says *this idea has no home in this format, express it another way*.

## The table

One column per format, and one row per capability. Two bounds separated by `/` are canonical and
structural; a single bound is a field with no headroom.

| Capability | Impulse Tracker | FastTracker 2 |
|---|---|---|
| `channels` | 1..64 / 1..127 | 1..32 / 1..192 |
| `patterns` | 0..200 / 0..254 | 0..256 |
| `orders` | 0..256 / 0..65535 | 0..256 |
| `pattern_rows` | 32..200 / 1..200 | 1..256 |
| `pattern_bytes` | 0..65535 | 0..65535 |
| `instruments` | 0..255 | 0..128 / 0..255 |
| `samples` | 0..255 | 0..2048 |
| `samples_per_instrument` | 0..255 | 0..16 / 0..255 |
| `sample_frames` | 0..4294967295 | 0..2147483647 |
| `sample_rate` | 1..9999999 | 10..25662141 |
| `sample_volume` | 0..64 | 0..64 |
| `sample_gain` | 0..64 | 64..64 |
| `instrument_volume` | 0..128 | 128..128 |
| `envelope_points` | 1..25 | 1..12 |
| `envelope_value` | -128..127 | 0..64 |
| `envelope_tick` | 0..65535 | 0..65535 |
| `fadeout` | 0..128 / 0..65535 | 0..4095 / 0..65535 |
| `note` | 0..119 | 0..95 |
| `tempo` | 32..255 | 32..255 / 1..65535 |
| `speed` | 1..255 | 1..31 / 1..65535 |
| `volume` | 0..64 | 0..64 |
| `volume_command` | 0..9 | 0..15 |
| `volume_panning` | 0..64 | 0..15 |
| `song_volume` | 0..128 | — |
| `mix_volume` | 0..128 | — |
| `message_bytes` | 0..8000 / 0..65535 | — |
| `panning` | 0..255 | 0..255 |

A dash means the format declares no capacity at all, and `limits.bound(...)` raises `KeyError` for it.
FastTracker 2 has no song-wide volume, no mix volume and no song message, so there is nothing to bound;
a caller reaching for one is asking about a field that does not exist, which is a different mistake from
asking for a value out of range.

Two capacities are pinned to a single value for the same reason: `sample_gain` at 64 and
`instrument_volume` at 128 say that FastTracker 2 applies no such multiplier. A song asking for a
quieter sample gain is told so.

`samples` and `instruments` stay at 255 for Impulse Tracker at both levels, and the reason is a
**reference** rather than a count. The header counts each in a sixteen-bit field, so the table itself has
room to spare — but an instrument names its sample in one byte of its note map, and a pattern cell names
its instrument in one byte too. A module numbering more than 255 of either would carry waveforms no
keymap can reach, so the byte that names one is the bound worth stating.

## Where each extended bound comes from

A caller choosing `EXTENDED` is choosing a bound the original tracker never honoured, so each one says
where it comes from. A bound is **structural**, provable from the record layout, or **observed**, taken
from what the players descended from these trackers read.

| Bound | Why it reaches that far |
|---|---|
| IT channels 64 → **127** | Structural. A packed cell announces its channel with the byte `(channel + 1) \| 0x80`, so the channel number occupies seven bits. |
| IT patterns 200 → **254** | Structural. The header counts patterns in sixteen bits, and an order-list entry is a byte whose `0xFE` and `0xFF` are the separator and the end of song — so an order names `0..253`, and 254 patterns are reachable. Impulse Tracker's own editor keeps 200. |
| IT orders 256 → **65535** | Structural. The header's order count is a sixteen-bit field, and the order table is written at whatever length it declares. |
| IT pattern rows floor 32 → **1** | Structural. The pattern header stores the row count in sixteen bits; the floor of 32 is Impulse Tracker's own editing convention. |
| IT message 8000 → **65535** | Structural. The header states the block's length in sixteen bits and points at it with a thirty-two-bit offset, so the record holds whatever that length reaches; 8000 bytes is what the editor keeps. |
| IT fadeout 128 → **65535** | Structural. The header's fadeout is a sixteen-bit field, and 128 is where Impulse Tracker's own editor stops. |
| XM instruments 128 → **255** | Structural. A pattern cell names its instrument in one byte, so 255 is as far as a cell reaches; 128 is FastTracker 2's own editing ceiling. |
| XM samples per instrument 16 → **255** | Structural. An instrument's keymap names a sample in one byte per key, so one instrument routes to 255 of them; 16 is the editor's own. |
| XM tempo 255 → **65535** | Structural. The header's tempo is a sixteen-bit field, and a row lasts `speed * 5 / (2 * tempo)` seconds at whatever it holds. |
| XM speed 31 → **65535** | Structural. The header's speed is a sixteen-bit field. |
| XM fadeout 4095 → **65535** | Structural. The header's fadeout is a sixteen-bit field, and `0xFFF` is where FastTracker 2's own editor stops. |
| XM channels 32 → **192** | Observed. The header's channel count is a sixteen-bit field, and 192 is the width the players descended from FastTracker 2 read. |

The IT tempo bound stays at **255 at both levels**, and this is the one place the distinction earns its
keep by refusing something. Impulse Tracker's header tempo is a single byte at offset 51. A tempo of 441
does not overflow into a slower song — it cannot be written at all. Reporting it as a `STRUCTURAL`
violation is the difference between a clear message and a `struct.error` from deep inside a writer.

The effect column is bounded separately from the header, because it is a separate field. FastTracker 2's
`Fxx` carries one parameter byte, so a **mid-song** tempo change tops out at 255 even in a module whose
header carries 441. `XM_EFFECTS.set_tempo(441)` raises; the header still holds it.

## Choosing a level

`Compliance.CANONICAL` is the level to write for a module that has to open in the tracker it names.
`Compliance.EXTENDED` is the level for a module that has to play — in OpenMPT, in libopenmpt, in
anything descended from them. Parsing defaults to `EXTENDED`, because a file that exists is evidence
that its values were storable.

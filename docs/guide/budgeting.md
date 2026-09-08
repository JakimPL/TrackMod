# Finding out how large a file will be

`module.size()` tells you what a song already costs. To ask earlier — how many bytes would one more sample
add? — use `module.storage`. It is a table of what each kind of content costs in that format:

```python
from trackmod import BitDepth, Compliance, ITModule

storage = ITModule.from_song(song, compliance=Compliance.CANONICAL).storage

storage.sample_bytes(frames=22050, depth=BitDepth.SIXTEEN)   # the records and the frames together
storage.instrument_bytes(samples=4)                          # the header this instrument is written in
storage.frames_budget(48_000, depth=BitDepth.SIXTEEN)        # the longest waveform that still fits
```

Each count covers the table entry a section occupies as well as the record itself, so a format that finds
its sections through offset tables charges that entry here, where you budget against one number.

`sample` is charged per stored slot: once per waveform where the sample table is shared, and once per owner
where each instrument owns its samples.

## Padding

The table also states the boundary a format's blocks start on, and every count above is rounded up to it, so
your budget covers the padding as well as the bytes. `storage.alignment` is:

* one byte, where a file lays its content down back to back,
* a word, where a record counts its length in pairs of frames,
* a paragraph, where a pointer names one.

## How the table relates to the size report

Each format's size model reads this same table, so `SizeReport.headers` *is* the table evaluated against the
counts a song declares. The table and the writer therefore agree by construction.

Adding an instrument and its sample grows the file by exactly what `instrument_bytes` and `sample_bytes`
predicted, for the three formats that lay their blocks down back to back. For the one that starts each block
on a paragraph, the growth is at most that, because one more table entry may push the tables onto the next
paragraph.

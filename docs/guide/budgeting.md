# Finding out how large a file will be

`module.size()` reports what a song costs now. To ask before you add anything (how many bytes would one
more sample cost?) use `module.storage`. It is a table of what each kind of content costs in that format:

```python
from trackmod import BitDepth, Compliance, ITModule

storage = ITModule.from_song(song, compliance=Compliance.CANONICAL).storage

storage.sample_bytes(frames=22050, depth=BitDepth.SIXTEEN)   # the records and the frames together
storage.instrument_bytes(samples=4)                          # the header this instrument is written in
storage.frames_budget(48_000, depth=BitDepth.SIXTEEN)        # the longest waveform that still fits
```

Every count includes the table entry that a section occupies, along with the record itself. A format that
finds its sections through offset tables charges that entry here, so you can budget against a single number.

A sample is charged once for each place the file stores it. A format with one shared sample table stores
each waveform once. A format where each instrument owns its samples stores a waveform once for every
instrument that owns it.

## Padding

Each format starts its blocks on a fixed boundary, and every count above is rounded up to it, so your
budget includes the padding as well as the data. `storage.alignment` is:

* one byte, when the file lays its content down back to back,
* one word, when a record counts its length in pairs of frames,
* one paragraph, when pointers address blocks in paragraphs.

## How the table relates to the size report

Each format's size model reads this same table. The `headers` figure in a size report is therefore the
table applied to the counts in your song, and the table and the bytes the writer produces agree.

Adding an instrument and its sample grows the file by exactly what `instrument_bytes` and `sample_bytes`
predicted, for the three formats that lay their blocks down back to back. The format that starts each block
on a paragraph grows by at most that, because the new table entry may fit inside padding the tables already
have.

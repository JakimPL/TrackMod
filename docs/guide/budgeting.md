# Budgeting a file

`module.size()` answers what a song already costs. A caller filling a byte budget asks the question
earlier — how many bytes would one more sample add? — and `module.storage` answers it, as a table of what
each kind of content costs a format:

```python
from trackmod import BitDepth, Compliance, ITModule

storage = ITModule.from_song(song, compliance=Compliance.CANONICAL).storage

storage.sample_bytes(frames=22050, depth=BitDepth.SIXTEEN)   # records and frames together
storage.instrument_bytes(samples=4)                          # the header this instrument is written in
storage.frames_budget(48_000, depth=BitDepth.SIXTEEN)        # the longest waveform that still fits
```

Each count covers the table entry a section occupies as well as the record itself, so a format found
through offset tables charges the entry here, where a caller budgets against one number, and `sample` is
charged per stored **slot** — once per waveform where a sample table is shared, once per owner where an
instrument owns its samples.

The table also states the boundary a format's blocks open on, and every count above is rounded to it, so
what a caller budgets covers the padding as well as the bytes: `storage.alignment` is one byte where a
file lays its content down back to back, a word where a record counts its length in pairs of frames, and a
paragraph where a pointer names one.

The table is what each format's size model reads, so `SizeReport.headers` *is* the table evaluated against
the counts a song declares. What the table states and what the writer lays out therefore have one home,
and adding an instrument and its sample grows the file by what `instrument_bytes` and `sample_bytes`
predicted — exactly, for the three that lay their blocks down back to back, and by at most that for the
one that opens each of them on a paragraph, where one more table entry may tip the tables onto the next.

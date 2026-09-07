# Documentation

TrackMod reads and writes tracker modules through one format-agnostic model of a piece of music. These
documents take that apart from three directions: how to use it, what the model holds, and what each
format can carry.

## Start here

| Document | What it covers |
|---|---|
| [`guide/reading.md`](guide/reading.md) | Open a file, whatever wrote it, and read what it holds |
| [`guide/writing.md`](guide/writing.md) | Bind a song to a format, state its settings, write the bytes |
| [`guide/converting.md`](guide/converting.md) | Move a song from one format to another, and hold either |
| [`guide/instruments.md`](guide/instruments.md) | Take instruments out of a module and write them as files |
| [`guide/samples.md`](guide/samples.md) | Reach the waveforms, and write them out as audio |
| [`guide/budgeting.md`](guide/budgeting.md) | Ask what a file will cost before writing it |

## The reference

| Document | What it covers |
|---|---|
| [`reference/model.md`](reference/model.md) | The shared model: songs, patterns, voices, samples, instruments, timing |
| [`reference/limits.md`](reference/limits.md) | Capabilities, compliance levels, and where every bound comes from |
| [`reference/effects.md`](reference/effects.md) | The effect column, and the one vocabulary each format spells its own way |
| [`reference/volume.md`](reference/volume.md) | The volume column: one vocabulary, and what each format's byte reaches |

## The formats

See [`formats/README.md`](formats/README.md) for the five side by side, and where they disagree about one
field. Each has a document of its own, describing what it stores and where every byte sits.

| Document | Format |
|---|---|
| [`formats/it.md`](formats/it.md) | Impulse Tracker, `.it` |
| [`formats/xm.md`](formats/xm.md) | FastTracker 2, `.xm` |
| [`formats/mod.md`](formats/mod.md) | Amiga ProTracker, `.mod` |
| [`formats/s3m.md`](formats/s3m.md) | Scream Tracker 3, `.s3m` |
| [`formats/st.md`](formats/st.md) | Soundtracker, the fifteen-sample `.mod` layout |

## Working on TrackMod

| Document | What it covers |
|---|---|
| [`contributing/architecture.md`](contributing/architecture.md) | How the packages are layered, and what each one owns |
| [`contributing/documentation.md`](contributing/documentation.md) | How these documents are written |
| [`contributing/development.md`](contributing/development.md) | The tools, the tests and the gates a change passes |

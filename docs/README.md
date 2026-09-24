# Documentation

TrackMod reads and writes tracker modules through one shared model of a song. These documents cover it from
three sides: how to use the library, what the model holds, and what each format can store.

## Guides

How to do each task.

| Document | What it covers |
|---|---|
| [`guide/reading.md`](guide/reading.md) | Open a file and read what is inside it |
| [`guide/writing.md`](guide/writing.md) | Write a song to a file in a format you choose |
| [`guide/converting.md`](guide/converting.md) | Convert a song from one format to another |
| [`guide/instruments.md`](guide/instruments.md) | Take instruments out of a module and save them as files |
| [`guide/samples.md`](guide/samples.md) | Read the waveforms and save them as audio |
| [`guide/budgeting.md`](guide/budgeting.md) | Find out how large a file will be before you write it |

## Reference

The shared model and its limits.

| Document | What it covers |
|---|---|
| [`reference/model.md`](reference/model.md) | Songs, patterns, voices, samples, instruments, timing |
| [`reference/limits.md`](reference/limits.md) | Capabilities, compliance levels, and where every bound comes from |
| [`reference/effects.md`](reference/effects.md) | The effect column, and the one vocabulary each format spells its own way |
| [`reference/volume.md`](reference/volume.md) | The volume column: one vocabulary, and what each format's byte reaches |

## Formats

The byte layout of each format. See [`formats/README.md`](formats/README.md) for the five side by side, and
for the fields they disagree about.

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
| [`contributing/releasing.md`](contributing/releasing.md) | How a tag becomes a release on PyPI |

# TrackMod

## v0.2.0 [2026-09-25]

* Added support for Amiga ProTracker and Soundtracker (`.mod`) and Scream Tracker 3 (`.s3m`).
* Added saving and loading sounds as `.wav` files, keeping loops, tuning, volume and panning.
* Supported modules that go beyond their tracker's original limits.
* Fixed FastTracker 2 modules losing or mixing up sounds when saved, and names with special characters changing.
* Fixed modules failing to open: cut-off files, very long patterns and out-of-range values now load.
* Improved the documentation.
* Published on PyPI: `pip install trackmod` (Python 3.12 or newer).

## v0.1.0 [2026-09-05]

The first working version of TrackMod, for Impulse Tracker and FastTracker 2.

* Added reading and writing of Impulse Tracker (`.it`) and FastTracker 2 (`.xm`) modules, including notes, effects, volumes and Impulse Tracker's song message and channel and pattern names.
* Added conversion of a song between the two formats.
* Added instruments with export to `.iti` or `.xi`.
* Added sounds, including stereo, loops and reading of Impulse Tracker's compressed sounds.
* Added size budgeting to plan how many sounds fit.

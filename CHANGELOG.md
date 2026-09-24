# TrackMod

## v0.2.0

* Added reading and writing of five tracker formats: Impulse Tracker (`.it`), FastTracker 2 (`.xm`), Amiga
  ProTracker (`.mod`), Scream Tracker 3 (`.s3m`) and the fifteen-sample Soundtracker layout (`.mod`).
* Added one shared model of a song, so a song read from one format can be written in another.
* Added single instruments saved and read as `.iti` and `.xi` files.
* Added waveforms saved and read as `.wav` files, with their loop points, tuning, volume, panning and
  auto-vibrato.
* Added format detection from the file contents, so a renamed file still opens.
* Added file size reports and format limit checks before a song is written.
* Added repair warnings for every value a file stores out of range.

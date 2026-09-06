from collections.abc import Sequence
from typing import Final

from trackmod.core.instruments.instrument import Instrument
from trackmod.core.notes.pitch import Note
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.song import Song
from trackmod.spec.pitch import RATE_NOTE
from trackmod.trackers.xm.addressing import routed
from trackmod.trackers.xm.instruments.group import SampleGroup
from trackmod.trackers.xm.spec.sizes import KEYMAP_NOTES
from trackmod.trackers.xm.tuning import Tuning, tuned_rate, tuning_for

FIRST_SLOT: Final = 0


def local_slots(instrument: Instrument) -> dict[int, int]:
    """Which position each sample the keys reach takes within the instrument, in the song's own order.

    An instrument stores its samples in one run and a key names one by its place in that run, so taking
    them in the order the song's table holds them is what lets a module read from this format and written
    back state its samples in the run it stated them in.
    """
    return {sample: slot for slot, sample in enumerate(sorted(instrument.samples))}


def stated_tuning(sample: Sample) -> Tuning | None:
    """The transposition a sample carries from a file of this format, while it still names its rate.

    A sample read back keeps the two bytes its header held, and they serve as long as they state the
    rate it plays at -- which is what tells a stored pair apart from the default a sample built anywhere
    else carries.
    """
    stored = Tuning(relative_note=sample.relative_note, finetune=sample.finetune)
    reference = Note(RATE_NOTE)
    return stored if tuned_rate(stored, key=reference, sounded=reference) == sample.rate else None


def key_tuning(sample: Sample, *, key: Note, sounded: Note) -> Tuning:
    """The transposition one key wants of a sample, in the spelling the sample already carries.

    A key sounding its own pitch wants exactly the shift a stored pair names, so writing those two bytes
    back is what makes a file this library reads and writes state the tuning it started with. Every other
    routing, and every sample reaching this format from elsewhere, is tuned from the rate it plays at.
    """
    stored = stated_tuning(sample)
    if stored is not None and sounded == key:
        return stored

    return tuning_for(sample.rate, key=key, sounded=sounded)


def slot_tuning(instrument: Instrument, sample: Sample, *, index: int) -> Tuning:
    """The one transposition that serves every key routed to a sample.

    A stored sample is transposed once, so the keys that reach it must all want the same shift. Keys
    that sound their own pitch always agree, and so does a whole-instrument transposition; a keymap that
    shifts one key differently from another is asking for something the format cannot store.

    Raises:
        ValueError: when two keys routed to the same sample want different transpositions.
    """
    agreed: Tuning | None = None
    for key in range(KEYMAP_NOTES):
        assignment = instrument.keymap[key]
        if assignment is None or assignment.sample != index:
            continue

        tuning = key_tuning(sample, key=Note(key), sounded=assignment.note)
        if agreed is None:
            agreed = tuning
        elif tuning != agreed:
            raise ValueError(
                f"instrument {instrument.name!r} transposes sample {index} differently on key {Note(key)}, "
                "which this format stores one transposition for"
            )

    if agreed is None:
        raise ValueError(f"instrument {instrument.name!r} routes no key to sample {index}")

    return agreed


def group_samples(instrument: Instrument, samples: Sequence[Sample]) -> SampleGroup:
    """The samples one instrument owns, the keymap that reaches them and how each one is tuned."""
    slots = local_slots(instrument)
    owned = tuple(samples[index] for index in slots)
    tunings = tuple(slot_tuning(instrument, samples[index], index=index) for index in slots)
    keymap = tuple(
        FIRST_SLOT if (assignment := instrument.keymap[key]) is None else slots[assignment.sample]
        for key in range(KEYMAP_NOTES)
    )
    return SampleGroup(samples=owned, tunings=tunings, keymap=keymap)


def song_groups(song: Song) -> tuple[SampleGroup, ...]:
    """Every instrument's samples, in the order the file lays them out.

    Raises:
        ValueError: when the song's cells name samples, which this format keeps no records for.
    """
    voices = routed(song)
    return tuple(group_samples(instrument, voices.samples) for instrument in voices.instruments)

import pytest

from tests.conftest import voices_of
from trackmod.core.repairs.report import RepairWarning
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import InstrumentVoices, SampleVoices
from trackmod.limits.capability import Capability
from trackmod.limits.compliance import Compliance
from trackmod.trackers.it.addressing import names_instruments, stated_flags
from trackmod.trackers.it.layout.file import FILE_HEADER
from trackmod.trackers.it.module import ITModule
from trackmod.trackers.it.spec.flags import HeaderFlag
from trackmod.trackers.it.spec.storage import IT_STORAGE

FLAGS_AT = next(field.offset for field in FILE_HEADER.fields if field.name == "flags")
FLAGS_BYTES = 2
RESERVED_BIT = 0x0400


def sample_addressed(song: Song) -> Song:
    """The shared song with its cells naming samples, which is the other way this format plays."""
    return song.model_copy(update={"voices": SampleVoices(samples=voices_of(song).samples)})


def module(song: Song) -> ITModule:
    return ITModule.from_song(song, compliance=Compliance.EXTENDED)


def stored_flags(data: bytes) -> HeaderFlag:
    """The switches the written header states."""
    return HeaderFlag(int.from_bytes(data[FLAGS_AT : FLAGS_AT + FLAGS_BYTES], "little"))


def test_a_song_whose_cells_name_instruments_switches_instruments_on(song: Song) -> None:
    assert names_instruments(stored_flags(module(song).to_bytes()))


def test_a_song_whose_cells_name_samples_switches_instruments_off(song: Song) -> None:
    data = module(sample_addressed(song)).to_bytes()
    assert not names_instruments(stored_flags(data))


def test_a_song_whose_cells_name_samples_writes_no_instrument_records(song: Song) -> None:
    saved = len(module(song).to_bytes()) - len(module(sample_addressed(song)).to_bytes())
    assert saved == sum(
        IT_STORAGE.instrument_bytes(samples=len(instrument.samples)) for instrument in voices_of(song).instruments
    )


def test_a_song_whose_cells_name_samples_parses_back_naming_samples(song: Song) -> None:
    flat = sample_addressed(song)
    recovered = ITModule.parse(module(flat).to_bytes()).song
    assert isinstance(recovered.voices, SampleVoices)
    assert recovered.voices.slots == flat.voices.slots
    assert [sample.name for sample in recovered.voices.samples] == [sample.name for sample in flat.voices.samples]


def test_writing_a_parsed_sample_addressed_module_reproduces_its_bytes(song: Song) -> None:
    data = module(sample_addressed(song)).to_bytes()
    assert ITModule.parse(data).to_bytes() == data


def test_a_song_whose_cells_name_samples_counts_no_instruments(song: Song) -> None:
    reported = module(sample_addressed(song)).violations()
    assert reported == ()
    graded = ITModule.from_song(sample_addressed(song), compliance=Compliance.CANONICAL).violations()
    assert Capability.INSTRUMENTS not in [violation.capability for violation in graded]


def test_a_file_switching_instruments_off_leaves_the_definitions_it_kept_aside(song: Song) -> None:
    # Impulse Tracker holds an instrument's definition ready for the switch going back on, and a song
    # playing samples sounds it nowhere.
    data = bytearray(module(song).to_bytes())
    cleared = HeaderFlag(int(stored_flags(bytes(data))) & ~int(HeaderFlag.USE_INSTRUMENTS))
    data[FLAGS_AT : FLAGS_AT + FLAGS_BYTES] = int(cleared).to_bytes(FLAGS_BYTES, "little")

    with pytest.warns(RepairWarning, match="instruments left aside"):
        recovered = ITModule.parse(bytes(data)).song

    assert isinstance(recovered.voices, SampleVoices)
    assert len(recovered.voices.samples) == len(voices_of(song).samples)


def test_the_instruments_switch_states_what_the_song_names_and_keeps_every_other_bit() -> None:
    carried = HeaderFlag(int(HeaderFlag.STEREO | HeaderFlag.LINEAR_SLIDES) | RESERVED_BIT)
    instruments = InstrumentVoices(instruments=(), samples=())
    samples = SampleVoices(samples=())

    switched_on = stated_flags(carried, instruments)
    switched_off = stated_flags(carried | HeaderFlag.USE_INSTRUMENTS, samples)

    assert names_instruments(switched_on)
    assert not names_instruments(switched_off)
    for flags in (switched_on, switched_off):
        assert flags & HeaderFlag.STEREO
        assert flags & HeaderFlag.LINEAR_SLIDES
        assert int(flags) & RESERVED_BIT

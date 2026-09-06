from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np
import pytest
from numpy.typing import NDArray

from tests.conftest import FADEOUT, keyed, lattice, rescaled, voices_of
from trackmod.core.effects.catalog import EffectCatalog
from trackmod.core.effects.effect import Effect
from trackmod.core.envelopes.envelope import Envelope
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.transfer import combine, extract, held
from trackmod.core.instruments.unit import InstrumentUnit
from trackmod.core.notes.command import NoteCommand
from trackmod.core.notes.pitch import Note
from trackmod.core.patterns.builder import PatternBuilder
from trackmod.core.patterns.cell import Cell
from trackmod.core.patterns.column import Column
from trackmod.core.patterns.grid import Pattern
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.song import Song
from trackmod.core.voices.convert import flattened, raised
from trackmod.core.voices.voices import InstrumentVoices, SampleVoices
from trackmod.core.volumes.command import VolumeCommand, VolumeEffect
from trackmod.limits.capability import Capability
from trackmod.limits.checklist import Checklist
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import LimitError
from trackmod.limits.table import Limits
from trackmod.module.instrument import InstrumentFile
from trackmod.module.protocol import TrackerModule
from trackmod.module.storage import NO_PADDING, Storage
from trackmod.spec.levels import CENTRE_PANNING, MAX_VOLUME
from trackmod.spec.pitch import RATE_NOTE, REFERENCE_RATE
from trackmod.spec.width import NIBBLE_MAX
from trackmod.trackers.amiga.patterns.sizing import packed_bytes as mod_packed_bytes
from trackmod.trackers.amiga.spec.cells import CELL_BYTES as MOD_CELL_BYTES
from trackmod.trackers.amiga.spec.periods import CANONICAL_MAX_NOTE, CANONICAL_MIN_NOTE
from trackmod.trackers.amiga.spec.ranges import PATTERN_ROWS as MOD_PATTERN_ROWS
from trackmod.trackers.it.effects.catalog import IT_EFFECTS
from trackmod.trackers.it.instrument_file import ITInstrumentFile
from trackmod.trackers.it.limits import it_limits
from trackmod.trackers.it.module import ITModule
from trackmod.trackers.it.patterns.sizing import packed_bytes as it_packed_bytes
from trackmod.trackers.it.patterns.width import WIDTH_MARKER_BYTES
from trackmod.trackers.it.timing import TIMINGS as IT_TIMINGS
from trackmod.trackers.mod.effects.catalog import MOD_EFFECTS
from trackmod.trackers.mod.limits import mod_limits
from trackmod.trackers.mod.module import MODModule
from trackmod.trackers.mod.timing import TIMINGS as MOD_TIMINGS
from trackmod.trackers.registry import (
    EXTENSIONS,
    INSTRUMENT_EXTENSIONS,
    MODULE_EXTENSIONS,
    parse_voices,
    reads,
)
from trackmod.trackers.s3m.effects.catalog import S3M_EFFECTS
from trackmod.trackers.s3m.limits import s3m_limits
from trackmod.trackers.s3m.module import S3MModule
from trackmod.trackers.s3m.patterns.sizing import packed_bytes as s3m_packed_bytes
from trackmod.trackers.s3m.spec.sizes import PARAGRAPH_BYTES
from trackmod.trackers.s3m.timing import TIMINGS as S3M_TIMINGS
from trackmod.trackers.st.effects.catalog import ST_EFFECTS
from trackmod.trackers.st.limits import st_limits
from trackmod.trackers.st.module import STModule
from trackmod.trackers.st.timing import TIMINGS as ST_TIMINGS
from trackmod.trackers.xm.effects.catalog import XM_EFFECTS
from trackmod.trackers.xm.instrument_file import XMInstrumentFile
from trackmod.trackers.xm.limits import xm_limits
from trackmod.trackers.xm.module import XMModule
from trackmod.trackers.xm.patterns.sizing import packed_bytes as xm_packed_bytes
from trackmod.trackers.xm.spec.ranges import MAX_NOTE
from trackmod.trackers.xm.timing import TIMINGS as XM_TIMINGS
from trackmod.trackers.xm.tuning import tuned_rate, tuning_for

FRAME_RATE: Final = 44100
UNWRITTEN_EXTENSION: Final = ".med"
PORTABLE_SPEED: Final = 6
PORTABLE_TEMPO: Final = 125
PORTABLE_CHANNELS: Final = 4
PORTABLE_INSTRUMENTS: Final = 3
PORTABLE_ROWS: Final = (32, 64)
PORTABLE_SEED: Final = 0
GENERATED_SEEDS: Final = (1, 2, 3, 4)
EXTRA_FRAMES: Final = (64, 65)

HACKED_TEMPO: Final = 441
SAMPLED_FRAMES: Final = (32, 40, 24)

MUSIC_COLUMNS: Final = (Column.NOTE, Column.INSTRUMENT, Column.VOLUME)


def portable_rate(rate: int) -> int:
    """The nearest rate to ``rate`` that both formats carry unchanged.

    Impulse Tracker stores a playback rate as a whole number of hertz, while FastTracker 2 stores a
    transposition of the key that triggers it, on a lattice of ``1 / 128`` of a semitone. A rate already
    sitting on the coarser of the two lattices survives both, so a test comparing what the two formats
    recovered is comparing the music rather than the rounding.
    """
    reference = Note(RATE_NOTE)
    return tuned_rate(tuning_for(rate, key=reference, sounded=reference), key=reference, sounded=reference)


PORTABLE_AMOUNT = 9  # the furthest a rate reaches in the narrower of the two columns


def portable_volume(rng: np.random.Generator, draw: float) -> int | VolumeCommand | None:
    """A volume column both formats store: a level, or one of the seven commands each of them names."""
    if draw >= 0.7:
        return None

    if draw >= 0.6:
        return VolumeCommand(effect=VolumeEffect.VOLUME_SLIDE_DOWN, amount=int(rng.integers(0, PORTABLE_AMOUNT + 1)))

    return int(rng.integers(0, MAX_VOLUME + 1))


def portable_pattern(catalog: EffectCatalog, *, rows: int, seed: int) -> Pattern:
    """A grid both formats store, whose first row states every channel so the width is unambiguous.

    Impulse Tracker packs only the channels a row carries and lists nothing about the rest, so a module
    whose highest channel is silent throughout reads back narrower than it was written. Sounding the
    whole width once fixes what the pattern is.
    """
    rng = np.random.default_rng(seed)
    builder = PatternBuilder(rows=rows, channels=PORTABLE_CHANNELS)
    for channel in range(PORTABLE_CHANNELS):
        builder.place(0, channel, Cell(note=Note(RATE_NOTE), instrument=channel % PORTABLE_INSTRUMENTS))

    for row in range(1, rows):
        for channel in range(PORTABLE_CHANNELS):
            draw = rng.random()
            if draw < 0.25:
                continue

            builder.place(
                row,
                channel,
                Cell(
                    note=Note(int(rng.integers(0, MAX_NOTE + 1))) if draw < 0.85 else NoteCommand.OFF,
                    instrument=int(rng.integers(0, PORTABLE_INSTRUMENTS)) if draw < 0.8 else None,
                    volume=portable_volume(rng, draw),
                    effect=catalog.note_delay(int(rng.integers(0, NIBBLE_MAX + 1))) if draw > 0.9 else None,
                ),
            )

    return builder.build()


def portable_samples() -> tuple[Sample, ...]:
    """Waveforms both formats store frame for frame, at rates both reach and a panning both keep."""
    return (
        Sample(
            name="lead",
            pcm=lattice(np.linspace(-1.0, 1.0, 32)),
            rate=portable_rate(FRAME_RATE),
            panning=CENTRE_PANNING,
        ),
        Sample(
            name="bass",
            pcm=lattice(np.sin(np.linspace(0.0, 4.0 * np.pi, 40))),
            rate=portable_rate(FRAME_RATE // 2),
            volume=48,
            panning=CENTRE_PANNING,
        ),
        Sample(
            name="pad",
            pcm=lattice(np.linspace(1.0, -1.0, 24)),
            rate=portable_rate(FRAME_RATE),
            panning=CENTRE_PANNING,
        ),
    )


def portable_song(catalog: EffectCatalog, envelope: Envelope, *, seed: int) -> Song:
    """A song both formats write at canonical compliance, spelled with one format's effects.

    Every quantity it carries lives in the intersection of the two formats: keys inside the eight octaves
    one of them numbers, patterns above the row floor the other's canonical patterns keep, a speed inside
    the five bits one of them reads, rates on the coarser tuning lattice, and one instrument per sample
    so the format that keeps no shared sample table stores each waveform once.

    The effect column is the one column a song carries for a single format at a time, because an
    ``Effect`` holds the command byte its own format numbers. The catalogue that spells the intent is
    therefore what a caller picks, and it is a parameter here.
    """
    samples = portable_samples()
    instruments = tuple(
        Instrument(
            name=sample.name,
            keymap=keyed(sample=index),
            volume_envelope=envelope if index == 0 else None,
            fadeout=FADEOUT,
        )
        for index, sample in enumerate(samples)
    )
    return Song(
        name="portable",
        channels=PORTABLE_CHANNELS,
        patterns=tuple(portable_pattern(catalog, rows=rows, seed=seed + rows) for rows in PORTABLE_ROWS),
        order=OrderList(entries=(0, 1, 0)),
        voices=InstrumentVoices(instruments=instruments, samples=samples),
        playback=Playback(speed=PORTABLE_SPEED, tempo=PORTABLE_TEMPO),
    )


def sampled_pattern(effect: Callable[[int], Effect], *, seed: int) -> Pattern:
    """A grid every format stores, whose keys stay inside the three octaves the narrowest of them tabulates.

    The volume column is left out and so are the note commands: the format that names a sample from every
    cell states a period there and nothing else, so a column or a command it has no field for would be
    content rather than a quantity, and this grid is the one all of them carry.
    """
    rng = np.random.default_rng(seed)
    builder = PatternBuilder(rows=MOD_PATTERN_ROWS, channels=PORTABLE_CHANNELS)
    for channel in range(PORTABLE_CHANNELS):
        builder.place(0, channel, Cell(note=Note(RATE_NOTE), instrument=channel % PORTABLE_INSTRUMENTS))

    for row in range(1, MOD_PATTERN_ROWS):
        for channel in range(PORTABLE_CHANNELS):
            draw = rng.random()
            if draw < 0.25:
                continue

            builder.place(
                row,
                channel,
                Cell(
                    note=Note(int(rng.integers(CANONICAL_MIN_NOTE, CANONICAL_MAX_NOTE + 1))),
                    instrument=int(rng.integers(0, PORTABLE_INSTRUMENTS)) if draw < 0.8 else None,
                    effect=effect(int(rng.integers(0, NIBBLE_MAX + 1))) if draw > 0.9 else None,
                ),
            )

    return builder.build()


def sampled_samples() -> tuple[Sample, ...]:
    """Waveforms every format stores frame for frame, at the one rate all of their tunings state exactly."""
    return tuple(
        Sample(
            name=name,
            pcm=lattice(np.linspace(-1.0, 1.0, frames), BitDepth.EIGHT),
            rate=REFERENCE_RATE,
            depth=BitDepth.EIGHT,
            volume=volume,
        )
        for name, frames, volume in zip(("lead", "bass", "pad"), SAMPLED_FRAMES, (MAX_VOLUME, 48, MAX_VOLUME))
    )


def sampled_song(effect: Callable[[int], Effect], *, seed: int) -> Song:
    """A song whose cells name samples, in the quantities every format here writes at canonical compliance.

    This is the narrower of the two shared songs. Where the instrument-addressed one lives in the
    intersection of two formats, this one lives in the intersection of all of them: patterns at the one
    height Amiga ProTracker holds, keys inside its three tabulated octaves, waveforms at eight bits and
    an even number of frames, and the clock every module of that lineage starts on.
    """
    return Song(
        name="sampled",
        channels=PORTABLE_CHANNELS,
        patterns=tuple(sampled_pattern(effect, seed=seed + index) for index in range(len(PORTABLE_ROWS))),
        order=OrderList(entries=(0, 1, 0)),
        voices=SampleVoices(samples=sampled_samples()),
        playback=Playback(speed=PORTABLE_SPEED, tempo=PORTABLE_TEMPO),
    )


def it_binding(song: Song, compliance: Compliance) -> TrackerModule:
    return ITModule.from_song(song, compliance=compliance)


def xm_binding(song: Song, compliance: Compliance) -> TrackerModule:
    return XMModule.from_song(song, compliance=compliance)


def parse_it(data: bytes) -> TrackerModule:
    return ITModule.parse(data)


def parse_xm(data: bytes) -> TrackerModule:
    return XMModule.parse(data)


def mod_binding(song: Song, compliance: Compliance) -> TrackerModule:
    return MODModule.from_song(song, compliance=compliance)


def parse_mod(data: bytes) -> TrackerModule:
    return MODModule.parse(data)


def s3m_binding(song: Song, compliance: Compliance) -> TrackerModule:
    return S3MModule.from_song(song, compliance=compliance)


def parse_s3m(data: bytes) -> TrackerModule:
    return S3MModule.parse(data)


def it_song(envelope: Envelope, seed: int) -> Song:
    return portable_song(IT_EFFECTS, envelope, seed=seed)


def xm_song(envelope: Envelope, seed: int) -> Song:
    return portable_song(XM_EFFECTS, envelope, seed=seed)


def mod_song(envelope: Envelope, seed: int) -> Song:
    del envelope
    return sampled_song(MOD_EFFECTS.note_delay, seed=seed)


def s3m_song(envelope: Envelope, seed: int) -> Song:
    del envelope
    return sampled_song(S3M_EFFECTS.note_delay, seed=seed)


def st_binding(song: Song, compliance: Compliance) -> TrackerModule:
    return STModule.from_song(song, compliance=compliance)


def parse_st(data: bytes) -> TrackerModule:
    return STModule.parse(data)


def st_song(envelope: Envelope, seed: int) -> Song:
    del envelope
    return sampled_song(ST_EFFECTS.pattern_break, seed=seed)


def it_instrument(unit: InstrumentUnit, compliance: Compliance) -> InstrumentFile:
    return ITInstrumentFile.from_unit(unit, compliance=compliance)


def xm_instrument(unit: InstrumentUnit, compliance: Compliance) -> InstrumentFile:
    return XMInstrumentFile.from_unit(unit, compliance=compliance)


def parse_it_instrument(data: bytes) -> InstrumentFile:
    return ITInstrumentFile.parse(data)


def parse_xm_instrument(data: bytes) -> InstrumentFile:
    return XMInstrumentFile.parse(data)


@dataclass(frozen=True)
class Binding:
    """One format's binding of the shared model as a whole module, so a property is stated once for all.

    ``song`` is the shared song in the shape that format addresses its voices in and the quantities it
    holds, because the formats disagree about what a cell may name: one numbers instruments, one numbers
    samples, and one is written either way.

    """

    name: str
    catalog: EffectCatalog
    bind: Callable[[Song, Compliance], TrackerModule]
    parse: Callable[[bytes], TrackerModule]
    song: Callable[[Envelope, int], Song]
    limits: Callable[[Compliance], Limits]


@dataclass(frozen=True)
class InstrumentBinding:
    """One format's binding of a single instrument stored on its own, beside the module it also writes.

    Only the formats that number instruments write one on its own, so this is the smaller set — a format
    whose cells name samples has no instrument to store and no container to store it in.
    """

    module: Binding
    bind_unit: Callable[[InstrumentUnit, Compliance], InstrumentFile]
    parse_unit: Callable[[bytes], InstrumentFile]


IT_BINDING: Final = Binding(
    name="it", catalog=IT_EFFECTS, bind=it_binding, parse=parse_it, song=it_song, limits=it_limits
)
XM_BINDING: Final = Binding(
    name="xm", catalog=XM_EFFECTS, bind=xm_binding, parse=parse_xm, song=xm_song, limits=xm_limits
)
MOD_BINDING: Final = Binding(
    name="mod", catalog=MOD_EFFECTS, bind=mod_binding, parse=parse_mod, song=mod_song, limits=mod_limits
)
S3M_BINDING: Final = Binding(
    name="s3m", catalog=S3M_EFFECTS, bind=s3m_binding, parse=parse_s3m, song=s3m_song, limits=s3m_limits
)
ST_BINDING: Final = Binding(
    name="st", catalog=ST_EFFECTS, bind=st_binding, parse=parse_st, song=st_song, limits=st_limits
)

BINDINGS: Final = (IT_BINDING, XM_BINDING, MOD_BINDING, S3M_BINDING, ST_BINDING)
VOICED_BINDINGS: Final = (IT_BINDING, XM_BINDING)
SAMPLED_BINDINGS: Final = (MOD_BINDING, S3M_BINDING)


def widens(binding: Binding) -> bool:
    """Whether a format's records leave room for more channels than the tracker that wrote it read.

    Four of the five do, because each states its width in a field a later player read further. The one
    that states no width anywhere plays what its machine had and nothing else, so the question a wider
    reading answers never arises for it.
    """
    canonical = binding.limits(Compliance.CANONICAL).bound(Capability.CHANNELS).maximum
    return canonical < binding.limits(Compliance.EXTENDED).bound(Capability.CHANNELS).maximum


WIDENING_BINDINGS: Final = tuple(binding for binding in BINDINGS if widens(binding))

INSTRUMENT_BINDINGS: Final = (
    InstrumentBinding(module=IT_BINDING, bind_unit=it_instrument, parse_unit=parse_it_instrument),
    InstrumentBinding(module=XM_BINDING, bind_unit=xm_instrument, parse_unit=parse_xm_instrument),
)


@pytest.fixture(params=BINDINGS, ids=[binding.name for binding in BINDINGS])
def binding(request: pytest.FixtureRequest) -> Binding:
    """Each format binding in turn, so one test body covers every format."""
    return request.param


@pytest.fixture(params=WIDENING_BINDINGS, ids=[binding.name for binding in WIDENING_BINDINGS])
def widening(request: pytest.FixtureRequest) -> Binding:
    """Each format that states a width a later player read further, which is every one that states it."""
    return request.param


@pytest.fixture
def widened(widening: Binding, fade_envelope: Envelope) -> Song:
    """The shared song, in the shape and the effects of the widening binding under test."""
    return widening.song(fade_envelope, PORTABLE_SEED)


@pytest.fixture(params=INSTRUMENT_BINDINGS, ids=[binding.module.name for binding in INSTRUMENT_BINDINGS])
def instrument_binding(request: pytest.FixtureRequest) -> InstrumentBinding:
    """Each binding that stores one instrument on its own, which is the formats that number instruments."""
    return request.param


@pytest.fixture
def portable(binding: Binding, fade_envelope: Envelope) -> Song:
    """The shared song, in the shape and the effects of the binding under test."""
    return binding.song(fade_envelope, PORTABLE_SEED)


@pytest.fixture
def voiced(instrument_binding: InstrumentBinding, fade_envelope: Envelope) -> Song:
    """The shared instrument-addressed song, for the formats that store one instrument on its own."""
    return instrument_binding.module.song(fade_envelope, PORTABLE_SEED)


@pytest.fixture
def instrumented(fade_envelope: Envelope) -> Song:
    """The shared instrument-addressed song, for what holds of the formats that number instruments."""
    return portable_song(IT_EFFECTS, fade_envelope, seed=PORTABLE_SEED)


def music(song: Song) -> list[list[NDArray[np.int16]]]:
    """Every pattern's note, instrument and volume planes, which both formats carry identically."""
    return [[pattern.column(column) for column in MUSIC_COLUMNS] for pattern in song.patterns]


def recovered_song(binding: Binding, song: Song) -> Song:
    """The song a binding writes and reads back, which is the music that survived its format."""
    return binding.parse(binding.bind(song, Compliance.CANONICAL).to_bytes()).song


def written(module: TrackerModule) -> bytes:
    """Serialise a module held only as the shared protocol, which is how a caller stays format-agnostic."""
    return module.to_bytes()


def test_a_binding_answers_the_whole_module_surface(binding: Binding, portable: Song) -> None:
    module = binding.bind(portable, Compliance.CANONICAL)
    assert module.song == portable
    assert module.limits.compliance is Compliance.CANONICAL
    assert module.extension.startswith(".")
    assert module.violations() == ()
    assert module.size().total == len(written(module))
    assert module.storage.file <= module.size().headers


def one_more_voice(song: Song, sample: Sample) -> Song:
    """The same song carrying one more voice, added the way the song's own table is addressed.

    A table of samples grows by a sample; a table of instruments grows by an instrument beside the sample
    its keys reach, since that is what one more voice costs a format whose cells name instruments.
    """
    voices = song.voices
    match voices:
        case SampleVoices():
            return song.model_copy(update={"voices": SampleVoices(samples=(*voices.samples, sample))})
        case InstrumentVoices():
            return song.model_copy(
                update={
                    "voices": InstrumentVoices(
                        instruments=(
                            *voices.instruments,
                            Instrument(name=sample.name, keymap=keyed(len(voices.samples))),
                        ),
                        samples=(*voices.samples, sample),
                    )
                }
            )


def spare_sample(song: Song, frames: int) -> Sample:
    """One more waveform stored the way the song's own samples are, so a format writes it the same."""
    stored = song.voices.samples[0]
    return Sample(
        name="extra",
        pcm=lattice(np.linspace(-1.0, 1.0, frames), stored.depth),
        rate=stored.rate,
        depth=stored.depth,
    )


def over_prediction(storage: Storage) -> int:
    """How far a storage table may over-state one more voice, which is a boundary where blocks are padded."""
    return 0 if storage.alignment == NO_PADDING else storage.alignment


def test_a_song_inside_its_tracker_reaches_no_further(binding: Binding, portable: Song) -> None:
    module = binding.bind(portable, Compliance.CANONICAL)
    assert module.reach is Compliance.CANONICAL
    assert module.exceeded() == ()
    module.require_reach(Compliance.CANONICAL)


def test_a_song_past_its_tracker_reaches_the_level_above_it(widening: Binding, widened: Song) -> None:
    # Widening to what the players descended from the tracker read is the one change a format stating
    # its width has room for, so one body covers all of them: it still writes, and says what it cost.
    binding, portable = widening, widened
    widest = binding.bind(portable, Compliance.EXTENDED).limits.bound(Capability.CHANNELS).maximum
    wide = binding.bind(rescaled(portable, widest), Compliance.EXTENDED)

    assert wide.violations() == ()
    assert wide.reach is Compliance.EXTENDED
    assert [violation.capability for violation in wide.exceeded()] == [Capability.CHANNELS]
    assert wide.exceeded()[0].level is Compliance.CANONICAL

    wide.require_reach(Compliance.EXTENDED)
    with pytest.raises(LimitError, match="channels"):
        wide.require_reach(Compliance.CANONICAL)


def test_what_a_file_reaches_survives_being_written_and_read_back(widening: Binding, widened: Song) -> None:
    widest = widening.bind(widened, Compliance.EXTENDED).limits.bound(Capability.CHANNELS).maximum
    written = widening.bind(rescaled(widened, widest), Compliance.EXTENDED).to_bytes()
    assert widening.parse(written).reach is Compliance.EXTENDED


def test_a_file_is_read_at_the_level_that_says_its_values_were_storable(binding: Binding, portable: Song) -> None:
    # A file that exists is evidence its values fit the record layout, so reading holds a module to the
    # widest level and never complains; what it reaches past is asked for separately.
    data = binding.bind(portable, Compliance.CANONICAL).to_bytes()
    assert binding.parse(data).limits.compliance is Compliance.STRUCTURAL


@pytest.mark.parametrize("frames", EXTRA_FRAMES)
def test_the_storage_table_predicts_what_one_more_voice_costs(binding: Binding, portable: Song, frames: int) -> None:
    # A budget has to hold what it promised, so a prediction covers the padding as well as the bytes: to
    # the byte where a file lays its content down back to back, and to within one boundary where every
    # block opens on a paragraph and one more table entry may tip the tables onto the next.
    extra = spare_sample(portable, frames)
    grown = one_more_voice(portable, extra)
    storage = binding.bind(portable, Compliance.CANONICAL).storage
    growth = len(written(binding.bind(grown, Compliance.CANONICAL))) - len(
        written(binding.bind(portable, Compliance.CANONICAL))
    )
    predicted = storage.instrument_bytes(samples=1) + storage.sample_bytes(frames=extra.frames, depth=extra.depth)
    assert 0 <= predicted - growth <= over_prediction(storage)


def test_the_size_model_agrees_with_the_written_file(binding: Binding, portable: Song) -> None:
    module = binding.bind(portable, Compliance.CANONICAL)
    report = module.size()
    assert report.total == len(module.to_bytes())
    assert report.total == report.patterns + report.pcm + report.headers


def test_a_module_saves_under_its_own_extension(tmp_path: Path, binding: Binding, portable: Song) -> None:
    module = binding.bind(portable, Compliance.CANONICAL)
    path = tmp_path / f"portable{module.extension}"
    module.save(path)
    assert path.read_bytes() == module.to_bytes()
    assert binding.parse(path.read_bytes()).song.name == portable.name


@pytest.mark.parametrize("seed", GENERATED_SEEDS)
def test_a_generated_song_survives_being_written_and_read_back(
    binding: Binding,
    fade_envelope: Envelope,
    seed: int,
) -> None:
    song = binding.song(fade_envelope, seed)
    module = binding.bind(song, Compliance.CANONICAL)
    data = module.to_bytes()

    recovered = binding.parse(data)
    assert module.size().total == len(data)
    assert recovered.song.patterns == song.patterns
    assert recovered.song.playback == song.playback
    assert recovered.song.order.entries == song.order.entries
    assert recovered.to_bytes() == data


def sounded_waveforms(song: Song) -> list[dict[int, Sample]]:
    """What each instrument's keys actually sound, read through the table its keymap indexes into."""
    voices = voices_of(song)
    return [
        {
            key: voices.samples[assignment.sample]
            for key, assignment in enumerate(instrument.keymap)
            if assignment is not None
        }
        for instrument in voices.instruments
    ]


def test_an_instrument_carried_between_songs_sounds_the_same_in_either_format(
    instrument_binding: InstrumentBinding,
    voiced: Song,
) -> None:
    # Reversing the order is what makes the renumbering matter: every keymap now indexes a table
    # position it was never built against, and a stale index would sound the wrong waveform.
    voices = voices_of(voiced)
    units = [extract(voices, index) for index in reversed(range(len(voices.instruments)))]
    reordered = voiced.model_copy(update={"voices": combine(units)})

    recovered = recovered_song(instrument_binding.module, reordered)
    for expected, restored in zip(reversed(sounded_waveforms(voiced)), sounded_waveforms(recovered)):
        assert set(restored) == set(expected)
        for key, sample in expected.items():
            assert restored[key].name == sample.name
            assert np.array_equal(restored[key].pcm, sample.pcm)


def both_recoveries(envelope: Envelope) -> tuple[Song, Song]:
    """One song written to both formats and read back, as each format recovered it."""
    from_it, from_xm = (recovered_song(binding, binding.song(envelope, PORTABLE_SEED)) for binding in VOICED_BINDINGS)
    return from_it, from_xm


def sampled_recoveries(envelope: Envelope) -> tuple[Song, Song]:
    """One song written to both formats whose cells name samples, as each of them recovered it."""
    from_mod, from_s3m = (
        recovered_song(binding, binding.song(envelope, PORTABLE_SEED)) for binding in SAMPLED_BINDINGS
    )
    return from_mod, from_s3m


def test_a_binding_answers_the_whole_instrument_file_surface(
    instrument_binding: InstrumentBinding,
    voiced: Song,
) -> None:
    unit = extract(voices_of(voiced), 0)
    written = instrument_binding.bind_unit(unit, Compliance.CANONICAL)
    assert written.unit == unit
    assert written.limits.compliance is Compliance.CANONICAL
    assert written.extension.startswith(".")
    assert written.violations() == ()
    assert written.size().total == len(written.to_bytes())


def test_an_instrument_stored_on_its_own_costs_less_than_the_module_around_it(
    instrument_binding: InstrumentBinding,
    voiced: Song,
) -> None:
    alone = instrument_binding.bind_unit(extract(voices_of(voiced), 0), Compliance.CANONICAL)
    whole = instrument_binding.module.bind(voiced, Compliance.CANONICAL)
    assert alone.size().total < whole.size().total


def test_a_unit_saves_under_the_extension_its_format_writes_instruments_with(
    tmp_path: Path,
    instrument_binding: InstrumentBinding,
    voiced: Song,
) -> None:
    written = instrument_binding.bind_unit(extract(voices_of(voiced), 0), Compliance.CANONICAL)
    path = tmp_path / f"voice{written.extension}"
    written.save(path)
    assert path.read_bytes() == written.to_bytes()
    parsed = instrument_binding.parse_unit(path.read_bytes())
    assert parsed.unit.instrument.name == voices_of(voiced).instruments[0].name


def test_the_registry_reads_a_module_by_the_extension_that_wrote_it(binding: Binding, portable: Song) -> None:
    module = binding.bind(portable, Compliance.CANONICAL)
    assert module.extension in MODULE_EXTENSIONS
    assert parse_voices(module.to_bytes(), extension=module.extension) == binding.parse(module.to_bytes()).song.voices


def test_the_registry_reads_a_standalone_instrument_as_the_one_voice_it_holds(
    instrument_binding: InstrumentBinding,
    voiced: Song,
) -> None:
    written = instrument_binding.bind_unit(extract(voices_of(voiced), 0), Compliance.CANONICAL)
    unit = instrument_binding.parse_unit(written.to_bytes()).unit
    assert written.extension in INSTRUMENT_EXTENSIONS
    assert parse_voices(written.to_bytes(), extension=written.extension) == InstrumentVoices(
        instruments=(unit.instrument,),
        samples=unit.samples,
    )


def test_the_registry_names_an_extension_however_it_is_spelled(binding: Binding, portable: Song) -> None:
    module = binding.bind(portable, Compliance.CANONICAL)
    assert reads(module.extension.upper())
    assert parse_voices(module.to_bytes(), extension=module.extension.upper()) == parse_voices(
        module.to_bytes(), extension=module.extension
    )


def test_the_registry_refuses_an_extension_no_format_here_writes() -> None:
    assert not reads(UNWRITTEN_EXTENSION)
    with pytest.raises(ValueError, match=UNWRITTEN_EXTENSION):
        parse_voices(b"", extension=UNWRITTEN_EXTENSION)


def test_both_formats_recover_the_same_voice_from_one_instrument(fade_envelope: Envelope) -> None:
    # Every quantity the unit carries lives in the intersection of the two formats, so what comes back
    # differing would be the container rather than the voice.
    unit = extract(voices_of(portable_song(IT_EFFECTS, fade_envelope, seed=PORTABLE_SEED)), 0)
    from_it, from_xm = (
        binding.parse_unit(binding.bind_unit(unit, Compliance.CANONICAL).to_bytes()).unit
        for binding in INSTRUMENT_BINDINGS
    )
    assert from_it.instrument.keymap == from_xm.instrument.keymap
    assert from_it.instrument.name == from_xm.instrument.name
    assert from_it.instrument.fadeout == from_xm.instrument.fadeout
    for restored, other in zip(from_it.samples, from_xm.samples):
        assert restored.name == other.name
        assert restored.rate == other.rate
        assert np.array_equal(restored.pcm, other.pcm)


def test_both_formats_recover_the_same_music_from_one_song(fade_envelope: Envelope) -> None:
    from_it, from_xm = both_recoveries(fade_envelope)
    assert from_it.name == from_xm.name
    assert from_it.channels == from_xm.channels
    assert from_it.playback == from_xm.playback
    assert from_it.order.entries == from_xm.order.entries
    for it_planes, xm_planes in zip(music(from_it), music(from_xm)):
        for it_plane, xm_plane in zip(it_planes, xm_planes):
            assert np.array_equal(it_plane, xm_plane)


def test_both_formats_recover_the_same_waveforms_from_one_song(fade_envelope: Envelope) -> None:
    from_it, from_xm = both_recoveries(fade_envelope)
    for original, restored in zip(from_it.voices.samples, from_xm.voices.samples):
        assert restored.name == original.name
        assert restored.rate == original.rate
        assert np.array_equal(restored.pcm, original.pcm)


def test_both_sample_addressed_formats_recover_the_same_music_from_one_song(fade_envelope: Envelope) -> None:
    # The song these two are given lives in the intersection of all four formats, so what the pair of
    # them recovered differing would be the container rather than the music.
    from_mod, from_s3m = sampled_recoveries(fade_envelope)
    assert from_mod.name == from_s3m.name
    assert from_mod.channels == from_s3m.channels
    assert from_mod.playback == from_s3m.playback
    assert from_mod.order.entries == from_s3m.order.entries
    for mod_planes, s3m_planes in zip(music(from_mod), music(from_s3m)):
        for mod_plane, s3m_plane in zip(mod_planes, s3m_planes):
            assert np.array_equal(mod_plane, s3m_plane)


def test_both_sample_addressed_formats_recover_the_same_waveforms_from_one_song(fade_envelope: Envelope) -> None:
    from_mod, from_s3m = sampled_recoveries(fade_envelope)
    for original, restored in zip(from_mod.voices.samples, from_s3m.voices.samples):
        assert restored.name == original.name
        assert restored.rate == original.rate
        assert np.array_equal(restored.pcm, original.pcm)


def test_silence_costs_each_format_something_different() -> None:
    # One format lists the channels that play, so silence is a terminator a row plus the one cell that
    # holds the width; one stores a full grid of masks, so silence costs a byte per cell; one stores
    # every column of every cell whatever it holds, so silence costs exactly what music costs; and one
    # lists the channels that play and states its own width elsewhere, so silence costs a byte a row.
    rows, channels = PORTABLE_ROWS[0], PORTABLE_CHANNELS
    empty = Pattern.empty(rows=rows, channels=channels)
    assert it_packed_bytes(empty) == rows + WIDTH_MARKER_BYTES
    assert xm_packed_bytes(empty) == rows * channels
    assert mod_packed_bytes(empty) == rows * channels * MOD_CELL_BYTES
    assert s3m_packed_bytes(empty) == rows


def test_every_format_reads_the_same_clock() -> None:
    frames = {
        row_frames(PORTABLE_SPEED, PORTABLE_TEMPO, frame_rate=FRAME_RATE)
        for row_frames in (
            IT_TIMINGS.row_frames,
            XM_TIMINGS.row_frames,
            MOD_TIMINGS.row_frames,
            S3M_TIMINGS.row_frames,
            ST_TIMINGS.row_frames,
        )
    }
    assert len(frames) == 1


def test_the_wider_tempo_field_reaches_shorter_rows() -> None:
    shortest_it = min(timing.row_frames for timing in IT_TIMINGS.exact_timings(frame_rate=FRAME_RATE, speed=1))
    shortest_xm = min(timing.row_frames for timing in XM_TIMINGS.exact_timings(frame_rate=FRAME_RATE, speed=1))
    assert shortest_xm < shortest_it


def test_a_format_declares_a_capacity_only_for_a_field_it_has() -> None:
    impulse = it_limits(Compliance.EXTENDED)
    fast_tracker = xm_limits(Compliance.EXTENDED)
    protracker = mod_limits(Compliance.EXTENDED)
    soundtracker = st_limits(Compliance.EXTENDED)
    addressed = {Capability.BLOCK_OFFSET, Capability.SAMPLE_OFFSET}
    assert set(protracker.capacities) == set(soundtracker.capacities)
    assert set(Capability) - set(impulse.capacities) == addressed | {Capability.SAMPLE_BYTES}
    assert set(Capability) - set(fast_tracker.capacities) == addressed | {
        Capability.SONG_VOLUME,
        Capability.MIX_VOLUME,
        Capability.MESSAGE_BYTES,
    }
    assert set(Capability) - set(protracker.capacities) == addressed | {
        Capability.PATTERN_BYTES,
        Capability.INSTRUMENTS,
        Capability.SAMPLES_PER_INSTRUMENT,
        Capability.INSTRUMENT_VOLUME,
        Capability.ENVELOPE_POINTS,
        Capability.ENVELOPE_VALUE,
        Capability.ENVELOPE_TICK,
        Capability.FADEOUT,
        Capability.VOLUME_COMMAND,
        Capability.VOLUME_PANNING,
        Capability.SONG_VOLUME,
        Capability.MIX_VOLUME,
        Capability.MESSAGE_BYTES,
    }
    with pytest.raises(ValueError, match="keeps no field for song_volume"):
        fast_tracker.bound(Capability.SONG_VOLUME)

    scream_tracker = s3m_limits(Compliance.EXTENDED)
    assert set(Capability) - set(scream_tracker.capacities) == {
        Capability.INSTRUMENTS,
        Capability.SAMPLES_PER_INSTRUMENT,
        Capability.INSTRUMENT_VOLUME,
        Capability.ENVELOPE_POINTS,
        Capability.ENVELOPE_VALUE,
        Capability.ENVELOPE_TICK,
        Capability.FADEOUT,
        Capability.VOLUME_COMMAND,
        Capability.MESSAGE_BYTES,
    }
    with pytest.raises(ValueError, match="keeps no field for envelope_points"):
        protracker.bound(Capability.ENVELOPE_POINTS)

    with pytest.raises(ValueError, match="keeps no field for fadeout"):
        scream_tracker.bound(Capability.FADEOUT)


def volume_panned() -> Pattern:
    """A grid whose one cell states a volume-column panning, which three of the four columns hold."""
    builder = PatternBuilder(rows=MOD_PATTERN_ROWS, channels=PORTABLE_CHANNELS)
    builder.place(
        0,
        0,
        Cell(
            note=Note(RATE_NOTE),
            instrument=0,
            volume=VolumeCommand(effect=VolumeEffect.PANNING, amount=0),
        ),
    )
    return builder.build()


def panning_stated(song: Song) -> Song:
    """The same song carrying one more pattern, whose volume column states a panning."""
    return song.model_copy(update={"patterns": (*song.patterns, volume_panned())})


def graded(module: TrackerModule) -> set[Capability]:
    """Every capability a module reaches for while grading itself."""
    seen: set[Capability] = set()
    check = Checklist.check

    def record(checklist: Checklist, capability: Capability, value: int, *, subject: str) -> None:
        seen.add(capability)
        check(checklist, capability, value, subject=subject)

    with pytest.MonkeyPatch.context() as patched:
        patched.setattr(Checklist, "check", record)
        module.violations()

    return seen


def declaring(envelope: Envelope) -> tuple[tuple[TrackerModule, Limits], ...]:
    """Each format's module over a song stating every quantity that format declares a capacity for."""
    instrumented = (panning_stated(it_song(envelope, PORTABLE_SEED)), panning_stated(xm_song(envelope, PORTABLE_SEED)))
    sampled = (
        mod_song(envelope, PORTABLE_SEED),
        panning_stated(s3m_song(envelope, PORTABLE_SEED)),
        st_song(envelope, PORTABLE_SEED),
    )
    compliance = Compliance.EXTENDED
    return (
        (it_binding(instrumented[0], compliance), it_limits(compliance)),
        (xm_binding(instrumented[1], compliance), xm_limits(compliance)),
        (mod_binding(sampled[0], compliance), mod_limits(compliance)),
        (s3m_binding(sampled[1], compliance), s3m_limits(compliance)),
        (st_binding(sampled[2], compliance), st_limits(compliance)),
    )


def test_a_format_grades_every_capacity_it_declares(fade_envelope: Envelope) -> None:
    """Every declared capacity is reached by a check, and every check asks for a declared capacity.

    A capacity nothing grades is a ceiling a caller is promised and never held to; a check reaching for
    a capacity its format leaves undeclared is refused by name where it is met, which is what once cost
    a whole read surface over a single volume-column slide.
    """
    for module, limits in declaring(fade_envelope):
        assert graded(module) == set(limits.capacities)


def test_only_one_format_stores_a_tempo_past_the_byte(instrumented: Song) -> None:
    fast = instrumented.model_copy(update={"playback": Playback(speed=PORTABLE_SPEED, tempo=HACKED_TEMPO)})

    assert XMModule.from_song(fast, compliance=Compliance.EXTENDED).violations() == ()
    (relaxed,) = XMModule.from_song(fast, compliance=Compliance.CANONICAL).violations()
    assert relaxed.capability is Capability.TEMPO
    assert relaxed.level is Compliance.CANONICAL

    for compliance in Compliance:
        (refused,) = ITModule.from_song(fast, compliance=compliance).violations()
        assert refused.capability is Capability.TEMPO
        assert refused.level is Compliance.STRUCTURAL


def test_a_song_one_format_stores_and_another_cannot_reaches_a_level_and_none(instrumented: Song) -> None:
    """One song, two formats: the one whose word holds the tempo reaches a level, the other reaches none."""
    fast = instrumented.model_copy(update={"playback": Playback(speed=PORTABLE_SPEED, tempo=HACKED_TEMPO)})

    assert XMModule.from_song(fast, compliance=Compliance.EXTENDED).reach is Compliance.EXTENDED
    assert ITModule.from_song(fast, compliance=Compliance.STRUCTURAL).reach is None


def test_a_structural_violation_is_refused_at_every_compliance_level(instrumented: Song) -> None:
    fast = instrumented.model_copy(update={"playback": Playback(speed=PORTABLE_SPEED, tempo=HACKED_TEMPO)})
    for compliance in Compliance:
        with pytest.raises(LimitError) as raised:
            ITModule.from_song(fast, compliance=compliance).to_bytes()

        assert raised.value.violations[0].level is Compliance.STRUCTURAL


def test_a_format_stating_its_width_carries_more_channels_than_its_tracker_read(
    widening: Binding,
    widened: Song,
) -> None:
    # Each of them reaches a different width past what its own tracker read, so the width to widen to is
    # the one the format itself declares: whatever its record layout holds, above what the tracker used.
    widest = widening.bind(widened, Compliance.EXTENDED).limits.bound(Capability.CHANNELS).maximum
    wide = rescaled(widened, widest)
    assert widening.bind(wide, Compliance.EXTENDED).violations() == ()
    (reported,) = [
        violation
        for violation in widening.bind(wide, Compliance.CANONICAL).violations()
        if violation.capability is Capability.CHANNELS
    ]
    assert reported.level is Compliance.CANONICAL


def test_the_format_stating_no_width_holds_the_one_its_machine_played() -> None:
    # Four of the five state their width in a field a later player read further. The fifth states it
    # nowhere, so its records leave no wider reading to reach and the width is settled for good.
    settled = [binding.name for binding in BINDINGS if binding not in WIDENING_BINDINGS]
    assert settled == ["st"]
    for compliance in Compliance:
        bound = ST_BINDING.limits(compliance).bound(Capability.CHANNELS)
        assert bound.minimum == bound.maximum


def test_each_catalogue_spells_one_intent_in_its_own_bytes() -> None:
    impulse, fast_tracker = IT_EFFECTS.set_tempo(140), XM_EFFECTS.set_tempo(140)
    assert impulse.command != fast_tracker.command
    assert impulse.parameter == fast_tracker.parameter == 140


def test_one_format_reads_its_pattern_break_as_a_plain_row_number() -> None:
    # The decimal reading is Amiga ProTracker's, and everything descended from it kept the reading;
    # Impulse Tracker is the one that broke with it and states the row itself.
    assert IT_EFFECTS.pattern_break(16).parameter == 16
    assert XM_EFFECTS.pattern_break(16).parameter == 0x16
    assert MOD_EFFECTS.pattern_break(16).parameter == 0x16


def test_the_tempo_a_header_holds_is_beyond_what_an_effect_sets(instrumented: Song) -> None:
    fast = instrumented.model_copy(update={"playback": Playback(speed=PORTABLE_SPEED, tempo=HACKED_TEMPO)})
    assert XMModule.from_song(fast, compliance=Compliance.EXTENDED).to_bytes()
    with pytest.raises(ValueError):
        XM_EFFECTS.set_tempo(HACKED_TEMPO)


def test_each_format_states_which_kind_of_voice_its_cells_name(instrumented: Song) -> None:
    # Impulse Tracker plays both ways and states which in its header; FastTracker 2 numbers instruments
    # and Amiga ProTracker numbers samples, so each of those reaches the other kind through a named
    # conversion rather than a writer's guess.
    flat = instrumented.model_copy(update={"voices": flattened(voices_of(instrumented))})
    assert isinstance(flat.voices, SampleVoices)
    assert ITModule.from_song(flat, compliance=Compliance.CANONICAL).violations() == ()
    assert ITModule.from_song(instrumented, compliance=Compliance.CANONICAL).violations() == ()

    with pytest.raises(ValueError, match="name instruments"):
        XMModule.from_song(flat, compliance=Compliance.CANONICAL)

    with pytest.raises(ValueError, match="name samples"):
        MODModule.from_song(instrumented, compliance=Compliance.CANONICAL)


def test_raising_a_sample_table_writes_it_to_a_format_that_numbers_instruments(instrumented: Song) -> None:
    flat = flattened(voices_of(instrumented))
    lifted = instrumented.model_copy(update={"voices": raised(flat)})
    for binding in VOICED_BINDINGS:
        recovered = binding.parse(binding.bind(lifted, Compliance.CANONICAL).to_bytes()).song
        assert [sample.name for sample in recovered.voices.samples] == [sample.name for sample in flat.samples]


def test_a_sample_table_reaches_every_format() -> None:
    # The narrower shared song is the one Amiga ProTracker writes as it stands, and the two formats that
    # number instruments take it through the conversion giving each sample the instrument sounding it.
    flat = sampled_song(MOD_EFFECTS.note_delay, seed=PORTABLE_SEED)
    samples = flat.voices.samples
    lifted = flat.model_copy(update={"voices": raised(SampleVoices(samples=samples))})

    assert MOD_BINDING.bind(flat, Compliance.CANONICAL).violations() == ()
    assert S3M_BINDING.bind(flat, Compliance.CANONICAL).violations() == ()
    assert ST_BINDING.bind(flat, Compliance.CANONICAL).violations() == ()
    for binding in VOICED_BINDINGS:
        recovered = binding.parse(binding.bind(lifted, Compliance.CANONICAL).to_bytes()).song
        assert [sample.name for sample in recovered.voices.samples] == [sample.name for sample in samples]


def test_the_registry_reads_a_sample_addressed_module_as_a_sample_table(instrumented: Song) -> None:
    flat = instrumented.model_copy(update={"voices": flattened(voices_of(instrumented))})
    module = ITModule.from_song(flat, compliance=Compliance.CANONICAL)
    read = parse_voices(module.to_bytes(), extension=module.extension)
    assert isinstance(read, SampleVoices)
    assert read.slots == flat.voices.slots


def test_a_song_read_as_units_states_one_per_instrument(
    instrument_binding: InstrumentBinding,
    voiced: Song,
) -> None:
    module = instrument_binding.module.bind(voiced, Compliance.CANONICAL)
    recovered = voices_of(instrument_binding.module.parse(module.to_bytes()).song)
    assert held(recovered) == tuple(extract(recovered, index) for index in range(recovered.slots))


def test_the_suffix_table_names_every_extension_a_format_here_writes() -> None:
    # `EXTENSIONS` is what a caller filters a directory by, so it has to hold what the readers hold and
    # nothing else. The two module formats of one lineage share a suffix, so the set is the smaller one.
    assert EXTENSIONS == MODULE_EXTENSIONS | INSTRUMENT_EXTENSIONS
    assert MODULE_EXTENSIONS == {".it", ".xm", ".mod", ".s3m"}
    assert INSTRUMENT_EXTENSIONS == {".iti", ".xi"}
    assert all(reads(extension) for extension in EXTENSIONS)
    written = {
        binding.bind(sampled_song(MOD_EFFECTS.note_delay, seed=PORTABLE_SEED), c).extension
        for binding in SAMPLED_BINDINGS + (ST_BINDING,)
        for c in (Compliance.CANONICAL,)
    }
    assert written <= MODULE_EXTENSIONS

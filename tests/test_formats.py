from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np
import pytest
from numpy.typing import NDArray

from tests.conftest import keyed, lattice, rescaled
from trackmod.core.effects.catalog import EffectCatalog
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
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.order import OrderList
from trackmod.core.songs.playback import Playback
from trackmod.core.songs.song import Song
from trackmod.limits.capability import Capability
from trackmod.limits.compliance import Compliance
from trackmod.limits.error import LimitError
from trackmod.limits.severity import Severity
from trackmod.module.instrument import InstrumentFile
from trackmod.module.protocol import TrackerModule
from trackmod.spec.levels import CENTRE_PANNING, MAX_VOLUME
from trackmod.spec.pitch import RATE_NOTE
from trackmod.spec.width import NIBBLE_MAX
from trackmod.trackers.it.effects.catalog import IT_EFFECTS
from trackmod.trackers.it.instrument_file import ITInstrumentFile
from trackmod.trackers.it.limits import it_limits
from trackmod.trackers.it.module import ITModule
from trackmod.trackers.it.patterns.sizing import packed_bytes as it_packed_bytes
from trackmod.trackers.it.timing import exact_timings as it_exact_timings
from trackmod.trackers.it.timing import row_frames as it_row_frames
from trackmod.trackers.registry import (
    INSTRUMENT_EXTENSIONS,
    MODULE_EXTENSIONS,
    parse_units,
    reads,
)
from trackmod.trackers.xm.effects.catalog import XM_EFFECTS
from trackmod.trackers.xm.instrument_file import XMInstrumentFile
from trackmod.trackers.xm.limits import xm_limits
from trackmod.trackers.xm.module import XMModule
from trackmod.trackers.xm.patterns.sizing import packed_bytes as xm_packed_bytes
from trackmod.trackers.xm.spec.ranges import MAX_NOTE
from trackmod.trackers.xm.timing import exact_timings as xm_exact_timings
from trackmod.trackers.xm.timing import row_frames as xm_row_frames
from trackmod.trackers.xm.tuning import tuned_rate, tuning_for

FRAME_RATE: Final = 44100
UNWRITTEN_EXTENSION: Final = ".mod"
PORTABLE_SPEED: Final = 6
PORTABLE_TEMPO: Final = 125
PORTABLE_CHANNELS: Final = 4
PORTABLE_INSTRUMENTS: Final = 3
PORTABLE_ROWS: Final = (32, 64)
PORTABLE_SEED: Final = 0
GENERATED_SEEDS: Final = (1, 2, 3, 4)
EXTRA_FRAMES: Final = 64

HACKED_TEMPO: Final = 441
HACKED_CHANNELS: Final = 100

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
                    volume=int(rng.integers(0, MAX_VOLUME + 1)) if draw < 0.7 else None,
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
            fadeout=256,
        )
        for index, sample in enumerate(samples)
    )
    return Song(
        name="portable",
        channels=PORTABLE_CHANNELS,
        patterns=tuple(portable_pattern(catalog, rows=rows, seed=seed + rows) for rows in PORTABLE_ROWS),
        order=OrderList(entries=(0, 1, 0)),
        instruments=instruments,
        samples=samples,
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
    """One format's binding of the shared model, so a property is stated once and checked for both.

    Each format binds the model in two containers — a whole module and one instrument on its own — and a
    property that holds of both is stated once here.
    """

    name: str
    catalog: EffectCatalog
    bind: Callable[[Song, Compliance], TrackerModule]
    parse: Callable[[bytes], TrackerModule]
    bind_unit: Callable[[InstrumentUnit, Compliance], InstrumentFile]
    parse_unit: Callable[[bytes], InstrumentFile]


BINDINGS: Final = (
    Binding(
        name="it",
        catalog=IT_EFFECTS,
        bind=it_binding,
        parse=parse_it,
        bind_unit=it_instrument,
        parse_unit=parse_it_instrument,
    ),
    Binding(
        name="xm",
        catalog=XM_EFFECTS,
        bind=xm_binding,
        parse=parse_xm,
        bind_unit=xm_instrument,
        parse_unit=parse_xm_instrument,
    ),
)


@pytest.fixture(params=BINDINGS, ids=[binding.name for binding in BINDINGS])
def binding(request: pytest.FixtureRequest) -> Binding:
    """Each format binding in turn, so one test body covers both."""
    return request.param


@pytest.fixture
def portable(binding: Binding, fade_envelope: Envelope) -> Song:
    """The shared song, spelled with the effects of the binding under test."""
    return portable_song(binding.catalog, fade_envelope, seed=PORTABLE_SEED)


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


def test_the_storage_table_predicts_what_one_more_voice_costs(binding: Binding, portable: Song) -> None:
    extra = Sample(name="extra", pcm=lattice(np.linspace(-1.0, 1.0, EXTRA_FRAMES)), rate=portable_rate(FRAME_RATE))
    grown = portable.model_copy(
        update={
            "instruments": (*portable.instruments, Instrument(name="extra", keymap=keyed(len(portable.samples)))),
            "samples": (*portable.samples, extra),
        }
    )
    storage = binding.bind(portable, Compliance.CANONICAL).storage
    growth = len(written(binding.bind(grown, Compliance.CANONICAL))) - len(
        written(binding.bind(portable, Compliance.CANONICAL))
    )
    assert growth == storage.instrument_bytes(samples=1) + storage.sample_bytes(frames=extra.frames, depth=extra.depth)


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
    song = portable_song(binding.catalog, fade_envelope, seed=seed)
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
    return [
        {
            key: song.samples[assignment.sample]
            for key, assignment in enumerate(instrument.keymap)
            if assignment is not None
        }
        for instrument in song.instruments
    ]


def test_an_instrument_carried_between_songs_sounds_the_same_in_either_format(
    binding: Binding,
    portable: Song,
) -> None:
    # Reversing the order is what makes the renumbering matter: every keymap now indexes a table
    # position it was never built against, and a stale index would sound the wrong waveform.
    units = [extract(portable, index) for index in reversed(range(len(portable.instruments)))]
    instruments, samples = combine(units)
    reordered = portable.model_copy(update={"instruments": instruments, "samples": samples})

    recovered = recovered_song(binding, reordered)
    for expected, restored in zip(reversed(sounded_waveforms(portable)), sounded_waveforms(recovered)):
        assert set(restored) == set(expected)
        for key, sample in expected.items():
            assert restored[key].name == sample.name
            assert np.array_equal(restored[key].pcm, sample.pcm)


def both_recoveries(envelope: Envelope) -> tuple[Song, Song]:
    """One song written to both formats and read back, as each format recovered it."""
    from_it, from_xm = (
        recovered_song(binding, portable_song(binding.catalog, envelope, seed=PORTABLE_SEED)) for binding in BINDINGS
    )
    return from_it, from_xm


def test_a_binding_answers_the_whole_instrument_file_surface(binding: Binding, portable: Song) -> None:
    unit = extract(portable, 0)
    written = binding.bind_unit(unit, Compliance.CANONICAL)
    assert written.unit == unit
    assert written.limits.compliance is Compliance.CANONICAL
    assert written.extension.startswith(".")
    assert written.violations() == ()
    assert written.size().total == len(written.to_bytes())


def test_an_instrument_stored_on_its_own_costs_less_than_the_module_around_it(
    binding: Binding,
    portable: Song,
) -> None:
    alone = binding.bind_unit(extract(portable, 0), Compliance.CANONICAL)
    whole = binding.bind(portable, Compliance.CANONICAL)
    assert alone.size().total < whole.size().total


def test_a_unit_saves_under_the_extension_its_format_writes_instruments_with(
    tmp_path: Path,
    binding: Binding,
    portable: Song,
) -> None:
    written = binding.bind_unit(extract(portable, 0), Compliance.CANONICAL)
    path = tmp_path / f"voice{written.extension}"
    written.save(path)
    assert path.read_bytes() == written.to_bytes()
    assert binding.parse_unit(path.read_bytes()).unit.instrument.name == portable.instruments[0].name


def test_the_registry_reads_a_module_by_the_extension_that_wrote_it(binding: Binding, portable: Song) -> None:
    module = binding.bind(portable, Compliance.CANONICAL)
    assert module.extension in MODULE_EXTENSIONS
    assert parse_units(module.to_bytes(), extension=module.extension) == held(binding.parse(module.to_bytes()).song)


def test_the_registry_reads_a_standalone_instrument_as_the_one_voice_it_holds(
    binding: Binding,
    portable: Song,
) -> None:
    written = binding.bind_unit(extract(portable, 0), Compliance.CANONICAL)
    assert written.extension in INSTRUMENT_EXTENSIONS
    assert parse_units(written.to_bytes(), extension=written.extension) == (
        binding.parse_unit(written.to_bytes()).unit,
    )


def test_the_registry_names_an_extension_however_it_is_spelled(binding: Binding, portable: Song) -> None:
    module = binding.bind(portable, Compliance.CANONICAL)
    assert reads(module.extension.upper())
    assert parse_units(module.to_bytes(), extension=module.extension.upper()) == parse_units(
        module.to_bytes(), extension=module.extension
    )


def test_the_registry_refuses_an_extension_no_format_here_writes() -> None:
    assert not reads(UNWRITTEN_EXTENSION)
    with pytest.raises(ValueError, match=UNWRITTEN_EXTENSION):
        parse_units(b"", extension=UNWRITTEN_EXTENSION)


def test_both_formats_recover_the_same_voice_from_one_instrument(fade_envelope: Envelope) -> None:
    # Every quantity the unit carries lives in the intersection of the two formats, so what comes back
    # differing would be the container rather than the voice.
    unit = extract(portable_song(IT_EFFECTS, fade_envelope, seed=PORTABLE_SEED), 0)
    from_it, from_xm = (
        binding.parse_unit(binding.bind_unit(unit, Compliance.CANONICAL).to_bytes()).unit for binding in BINDINGS
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
    for original, restored in zip(from_it.samples, from_xm.samples):
        assert restored.name == original.name
        assert restored.rate == original.rate
        assert np.array_equal(restored.pcm, original.pcm)


def test_silence_costs_a_row_in_one_format_and_a_cell_in_the_other() -> None:
    rows, channels = PORTABLE_ROWS[0], PORTABLE_CHANNELS
    empty = Pattern.empty(rows=rows, channels=channels)
    assert it_packed_bytes(empty) == rows
    assert xm_packed_bytes(empty) == rows * channels


def test_both_formats_read_the_same_clock() -> None:
    assert it_row_frames(PORTABLE_SPEED, PORTABLE_TEMPO, frame_rate=FRAME_RATE) == xm_row_frames(
        PORTABLE_SPEED, PORTABLE_TEMPO, frame_rate=FRAME_RATE
    )


def test_the_wider_tempo_field_reaches_shorter_rows() -> None:
    shortest_it = min(timing.row_frames for timing in it_exact_timings(frame_rate=FRAME_RATE, speed=1))
    shortest_xm = min(timing.row_frames for timing in xm_exact_timings(frame_rate=FRAME_RATE, speed=1))
    assert shortest_xm < shortest_it


def test_a_format_declares_a_capacity_only_for_a_field_it_has() -> None:
    impulse = it_limits(Compliance.EXTENDED)
    fast_tracker = xm_limits(Compliance.EXTENDED)
    assert set(impulse.capacities) == set(Capability)
    assert set(Capability) - set(fast_tracker.capacities) == {
        Capability.SONG_VOLUME,
        Capability.MIX_VOLUME,
        Capability.MESSAGE_BYTES,
    }
    with pytest.raises(KeyError):
        fast_tracker.bound(Capability.SONG_VOLUME)


def test_only_one_format_stores_a_tempo_past_the_byte(portable: Song) -> None:
    fast = portable.model_copy(update={"playback": Playback(speed=PORTABLE_SPEED, tempo=HACKED_TEMPO)})

    assert XMModule.from_song(fast, compliance=Compliance.EXTENDED).violations() == ()
    (relaxed,) = XMModule.from_song(fast, compliance=Compliance.CANONICAL).violations()
    assert relaxed.capability is Capability.TEMPO
    assert relaxed.severity is Severity.COMPLIANCE

    for compliance in Compliance:
        (refused,) = ITModule.from_song(fast, compliance=compliance).violations()
        assert refused.capability is Capability.TEMPO
        assert refused.severity is Severity.STRUCTURAL


def test_a_structural_violation_is_refused_at_every_compliance_level(portable: Song) -> None:
    fast = portable.model_copy(update={"playback": Playback(speed=PORTABLE_SPEED, tempo=HACKED_TEMPO)})
    for compliance in Compliance:
        with pytest.raises(LimitError) as raised:
            ITModule.from_song(fast, compliance=compliance).to_bytes()

        assert raised.value.violations[0].severity is Severity.STRUCTURAL


def test_both_formats_carry_more_channels_than_their_tracker_reads(binding: Binding, portable: Song) -> None:
    wide = rescaled(portable, HACKED_CHANNELS)
    assert binding.bind(wide, Compliance.EXTENDED).violations() == ()
    (reported,) = [
        violation
        for violation in binding.bind(wide, Compliance.CANONICAL).violations()
        if violation.capability is Capability.CHANNELS
    ]
    assert reported.severity is Severity.COMPLIANCE


def test_each_catalogue_spells_one_intent_in_its_own_bytes() -> None:
    impulse, fast_tracker = IT_EFFECTS.set_tempo(140), XM_EFFECTS.set_tempo(140)
    assert impulse.command != fast_tracker.command
    assert impulse.parameter == fast_tracker.parameter == 140


def test_one_format_reads_its_pattern_break_as_decimal_digits() -> None:
    assert IT_EFFECTS.pattern_break(16).parameter == 16
    assert XM_EFFECTS.pattern_break(16).parameter == 0x16


def test_the_tempo_a_header_holds_is_beyond_what_an_effect_sets(portable: Song) -> None:
    fast = portable.model_copy(update={"playback": Playback(speed=PORTABLE_SPEED, tempo=HACKED_TEMPO)})
    assert XMModule.from_song(fast, compliance=Compliance.EXTENDED).to_bytes()
    with pytest.raises(ValueError):
        XM_EFFECTS.set_tempo(HACKED_TEMPO)

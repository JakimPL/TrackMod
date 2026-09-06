import struct
from pathlib import Path

import numpy as np
import pytest

from tests.conftest import keyed, lattice, revoiced, voices_of
from trackmod.binary.records.values import read_int
from trackmod.core.envelopes.envelope import Envelope
from trackmod.core.envelopes.point import EnvelopePoint
from trackmod.core.envelopes.span import EnvelopeSpan
from trackmod.core.instruments.instrument import Instrument
from trackmod.core.instruments.keymap import KeyAssignment, routed_keymap
from trackmod.core.notes.pitch import Note
from trackmod.core.repairs.report import RepairWarning
from trackmod.core.samples.loop import Loop
from trackmod.core.samples.sample import Sample
from trackmod.core.songs.song import Song
from trackmod.core.voices.voices import InstrumentVoices
from trackmod.limits.compliance import Compliance
from trackmod.spec.pitch import RATE_NOTE
from trackmod.trackers.xm.instruments.grouping import song_groups
from trackmod.trackers.xm.layout.file import FILE_HEADER
from trackmod.trackers.xm.layout.instrument import EMPTY_INSTRUMENT_HEADER
from trackmod.trackers.xm.layout.pattern import PATTERN_HEADER
from trackmod.trackers.xm.layout.sample import SAMPLE_HEADER
from trackmod.trackers.xm.module import XMModule
from trackmod.trackers.xm.patterns.sizing import packed_bytes
from trackmod.trackers.xm.settings import XMSettings
from trackmod.trackers.xm.spec.defaults import DEFAULT_SPEED
from trackmod.trackers.xm.spec.identity import MAGIC
from trackmod.trackers.xm.spec.sizes import (
    EMPTY_INSTRUMENT_HEADER_BYTES,
    FILE_HEADER_BYTES,
    HEADER_SIZE_OFFSET,
    INSTRUMENT_HEADER_BYTES,
    KEYMAP_NOTES,
    PATTERN_HEADER_BYTES,
    SAMPLE_HEADER_BYTES,
)
from trackmod.trackers.xm.spec.storage import XM_STORAGE
from trackmod.trackers.xm.tuning import Tuning, tuned_rate, tuning_for

SPEED_OFFSET = 76
KEYMAP_ORIGIN = 33

EXTRA_FRAMES = 64


def module(song: Song, *, compliance: Compliance = Compliance.EXTENDED) -> XMModule:
    return XMModule.from_song(song, compliance=compliance)


def test_the_file_opens_with_the_format_tag(xm_song: Song) -> None:
    assert module(xm_song).to_bytes().startswith(MAGIC)


def test_the_size_model_agrees_with_the_written_file(xm_song: Song) -> None:
    assert module(xm_song).size().total == len(module(xm_song).to_bytes())


def test_the_size_report_names_the_largest_pattern(xm_song: Song) -> None:
    report = module(xm_song).size()
    assert report.largest_pattern == max(packed_bytes(pattern) for pattern in xm_song.patterns)
    assert report.total == report.patterns + report.pcm + report.headers


def test_a_written_module_parses_back_to_the_same_song(xm_song: Song) -> None:
    recovered = XMModule.parse(module(xm_song).to_bytes()).song
    assert recovered.name == xm_song.name
    assert recovered.channels == xm_song.channels
    assert recovered.playback == xm_song.playback
    assert recovered.order == xm_song.order
    assert recovered.patterns == xm_song.patterns
    assert recovered.voices == xm_song.voices


def test_writing_a_parsed_module_reproduces_its_bytes(xm_song: Song) -> None:
    data = module(xm_song).to_bytes()
    assert XMModule.parse(data).to_bytes() == data


def test_sample_waveforms_survive_the_delta_encoding(xm_song: Song, xm_voices: InstrumentVoices) -> None:
    recovered = XMModule.parse(module(xm_song).to_bytes()).song
    for original, restored in zip(xm_voices.samples, recovered.voices.samples):
        assert np.allclose(restored.pcm, original.pcm, atol=1.5 / original.depth.scale)


def test_settings_survive_a_round_trip(xm_song: Song) -> None:
    settings = XMSettings(tracker="probe")
    written = XMModule(song=xm_song, compliance=Compliance.EXTENDED, settings=settings).to_bytes()
    assert XMModule.parse(written).settings == settings


def test_a_written_module_can_be_saved_and_loaded(tmp_path: Path, xm_song: Song) -> None:
    path = tmp_path / f"song{module(xm_song).extension}"
    module(xm_song).save(path)
    assert XMModule.load(path).song.name == xm_song.name


def test_parsing_something_that_is_not_a_module_raises() -> None:
    with pytest.raises(ValueError):
        XMModule.parse(b"not a module" + bytes(512))


def test_an_instrument_owning_nothing_is_written_in_the_short_form(
    xm_song: Song,
    xm_voices: InstrumentVoices,
) -> None:
    placeholder = Instrument(name="silent", keymap=(None,) * len(xm_voices.instruments[0].keymap))
    song = revoiced(xm_song, instruments=(placeholder, *xm_voices.instruments))
    written = module(song).to_bytes()
    recovered = XMModule.parse(written).song.voices
    assert len(written) == len(module(xm_song).to_bytes()) + EMPTY_INSTRUMENT_HEADER_BYTES
    assert EMPTY_INSTRUMENT_HEADER_BYTES < INSTRUMENT_HEADER_BYTES
    assert isinstance(recovered, InstrumentVoices)
    assert recovered.instruments[0].samples == ()


def test_one_more_instrument_and_its_sample_grow_the_file_by_what_the_table_charges(
    xm_song: Song,
    xm_voices: InstrumentVoices,
) -> None:
    extra = Sample(name="extra", pcm=lattice(np.linspace(-1.0, 1.0, EXTRA_FRAMES)), rate=44092)
    grown = revoiced(
        xm_song,
        instruments=(*xm_voices.instruments, Instrument(name="extra", keymap=keyed(len(xm_voices.samples)))),
        samples=(*xm_voices.samples, extra),
    )
    growth = len(module(grown).to_bytes()) - len(module(xm_song).to_bytes())
    assert growth == XM_STORAGE.instrument_bytes(samples=1) + XM_STORAGE.sample_bytes(
        frames=extra.frames, depth=extra.depth
    )


def test_a_sample_no_key_reaches_costs_this_format_nothing(xm_song: Song, xm_voices: InstrumentVoices) -> None:
    extra = Sample(name="unreached", pcm=lattice(np.linspace(-1.0, 1.0, EXTRA_FRAMES)), rate=44092)
    grown = revoiced(xm_song, samples=(*xm_voices.samples, extra))
    assert len(module(grown).to_bytes()) == len(module(xm_song).to_bytes())


def test_a_shared_sample_is_written_once_per_instrument_that_reaches_it(
    xm_song: Song,
    xm_voices: InstrumentVoices,
) -> None:
    sample = xm_voices.samples[0]
    sharing = tuple(Instrument(name=name, keymap=keyed(0)) for name in ("a", "b", "c"))
    song = revoiced(xm_song, instruments=sharing, samples=(sample,))
    assert [group.length for group in song_groups(song)] == [1, 1, 1]
    assert module(song).size().pcm == len(sharing) * sample.stored_bytes


def test_a_sustain_loop_this_format_cannot_store_is_refused(xm_song: Song, xm_voices: InstrumentVoices) -> None:
    looped = xm_voices.samples[0].model_copy(update={"sustain_loop": Loop(begin=0, end=8)})
    song = revoiced(xm_song, samples=(looped, *xm_voices.samples[1:]))
    with pytest.raises(ValueError, match="sustain loop"):
        module(song).to_bytes()


def test_a_stereo_sample_this_format_cannot_store_is_refused(xm_song: Song, xm_voices: InstrumentVoices) -> None:
    stereo = Sample(name="stereo", pcm=np.zeros((8, 2)), rate=44100)
    song = revoiced(xm_song, samples=(stereo, *xm_voices.samples[1:]))
    with pytest.raises(ValueError, match="stereo"):
        module(song).to_bytes()


def test_a_pitch_envelope_this_format_cannot_store_is_refused(xm_song: Song, xm_voices: InstrumentVoices) -> None:
    shaped = xm_voices.instruments[0].model_copy(
        update={"pitch_envelope": Envelope(points=(EnvelopePoint(tick=0, value=0),))}
    )
    song = revoiced(xm_song, instruments=(shaped, *xm_voices.instruments[1:]))
    with pytest.raises(ValueError, match="pitch envelope"):
        module(song).to_bytes()


def test_an_envelope_sustaining_over_a_span_is_refused(xm_song: Song, xm_voices: InstrumentVoices) -> None:
    over = Envelope(
        points=(EnvelopePoint(tick=0, value=64), EnvelopePoint(tick=8, value=32), EnvelopePoint(tick=16, value=0)),
        sustain=EnvelopeSpan(begin=0, end=1),
    )
    shaped = xm_voices.instruments[0].model_copy(update={"volume_envelope": over})
    song = revoiced(xm_song, instruments=(shaped, *xm_voices.instruments[1:]))
    with pytest.raises(ValueError, match="one point"):
        module(song).to_bytes()


def test_a_keymap_transposing_one_key_differently_from_another_is_refused(
    xm_song: Song,
    xm_voices: InstrumentVoices,
) -> None:
    uneven = Instrument(
        name="uneven",
        keymap=routed_keymap(
            {
                Note(60): KeyAssignment(sample=0, note=Note(60)),
                Note(61): KeyAssignment(sample=0, note=Note(72)),
            }
        ),
    )
    song = revoiced(xm_song, instruments=(uneven, *xm_voices.instruments[1:]))
    with pytest.raises(ValueError, match="transposes"):
        module(song).to_bytes()


def test_a_keymap_transposing_every_key_the_same_way_is_stored_once(
    xm_song: Song,
    xm_voices: InstrumentVoices,
) -> None:
    shifted = Instrument(
        name="shifted",
        keymap=routed_keymap(
            {
                Note(60): KeyAssignment(sample=0, note=Note(72)),
                Note(61): KeyAssignment(sample=0, note=Note(73)),
            }
        ),
    )
    song = revoiced(xm_song, instruments=(shifted, *xm_voices.instruments[1:]))
    group = song_groups(song)[0]
    assert group.length == 1
    assert group.tunings[0].relative_note == 12 + tuning_of(xm_voices.samples[0].rate)


def tuning_of(rate: int) -> int:
    reference = Note(RATE_NOTE)
    return tuning_for(rate, key=reference, sounded=reference).relative_note


def test_a_header_speed_of_zero_starts_the_song_at_this_format_s_own_speed(xm_song: Song) -> None:
    # Real files carry a speed of zero, which leaves a song no clock to advance on.
    data = bytearray(module(xm_song).to_bytes())
    data[SPEED_OFFSET : SPEED_OFFSET + 2] = (0).to_bytes(2, "little")

    with pytest.warns(RepairWarning, match="speed 0"):
        recovered = XMModule.parse(bytes(data)).song

    assert recovered.playback.speed == DEFAULT_SPEED
    assert recovered.playback.tempo == xm_song.playback.tempo


SHORTER_INSTRUMENT_HEADER = 243


def instrument_offsets(data: bytes) -> list[int]:
    """Where each instrument record opens, walked the way this format's own reader walks a file."""
    header = FILE_HEADER.unpack(data[:FILE_HEADER_BYTES])
    offset = HEADER_SIZE_OFFSET + read_int(header, "header_size")
    for _ in range(read_int(header, "pattern_count")):
        values = PATTERN_HEADER.unpack(data[offset : offset + PATTERN_HEADER_BYTES])
        offset += read_int(values, "header_length") + read_int(values, "packed_size")

    offsets = []
    for _ in range(read_int(header, "instrument_count")):
        offsets.append(offset)
        values = EMPTY_INSTRUMENT_HEADER.unpack(data[offset : offset + EMPTY_INSTRUMENT_HEADER_BYTES])
        count = read_int(values, "sample_count")
        offset += read_int(values, "header_size")
        headers = [
            SAMPLE_HEADER.unpack(data[offset + SAMPLE_HEADER_BYTES * slot :][:SAMPLE_HEADER_BYTES])
            for slot in range(count)
        ]
        offset += SAMPLE_HEADER_BYTES * count + sum(read_int(values, "length") for values in headers)

    return offsets


def shortened_headers(data: bytes) -> bytes:
    """The same module with every instrument header cut to the width a later writer states.

    The body an instrument header carries ends at its fadeout, and this format reserves what follows.
    Writers after FastTracker 2 state a length that stops there, so the record is genuinely shorter and
    the samples that follow it open earlier.
    """
    offsets = instrument_offsets(data)
    out = bytearray(data[: offsets[0]])
    for index, offset in enumerate(offsets):
        end = offsets[index + 1] if index + 1 < len(offsets) else len(data)
        record = bytearray(data[offset : offset + INSTRUMENT_HEADER_BYTES])
        struct.pack_into("<I", record, 0, SHORTER_INSTRUMENT_HEADER)
        out += record[:SHORTER_INSTRUMENT_HEADER]
        out += data[offset + INSTRUMENT_HEADER_BYTES : end]

    return bytes(out)


def test_an_instrument_stating_a_shorter_header_still_owns_the_samples_it_counts(xm_song: Song) -> None:
    # Writers after FastTracker 2 spend the header-length field their own way, and 243 is one of the
    # widths they state. The keymap and envelopes sit where this format puts them either way, so the
    # stated length says how far to step and nothing about which fields the record carries.
    recovered = XMModule.parse(shortened_headers(module(xm_song).to_bytes())).song.voices
    stated = voices_of(xm_song)
    assert isinstance(recovered, InstrumentVoices)
    assert [instrument.samples for instrument in recovered.instruments] == [
        instrument.samples for instrument in stated.instruments
    ]
    assert [sample.frames for sample in recovered.samples] == [sample.frames for sample in stated.samples]


def test_a_module_whose_instruments_state_a_shorter_header_writes_back_every_frame(xm_song: Song) -> None:
    written = XMModule.parse(shortened_headers(module(xm_song).to_bytes())).to_bytes()
    recovered = XMModule.parse(written).song.voices
    assert isinstance(recovered, InstrumentVoices)
    assert sum(sample.frames for sample in recovered.samples) == sum(
        sample.frames for sample in voices_of(xm_song).samples
    )


def test_the_transposition_a_header_states_is_the_one_written_back(xm_song: Song) -> None:
    # A stored pair spells a transposition one way where the arithmetic would spell it another: 29
    # semitones trimmed 28/128 down is the same pitch as 28 trimmed 100/128 up, and a file that stated
    # the first has to state it again after a rewrite.
    reference = Note(RATE_NOTE)
    stored = Tuning(relative_note=29, finetune=-28)
    voices = voices_of(xm_song)
    tuned = voices.samples[0].model_copy(
        update={
            "rate": tuned_rate(stored, key=reference, sounded=reference),
            "relative_note": stored.relative_note,
            "finetune": stored.finetune,
        }
    )
    song = revoiced(xm_song, samples=(tuned, *voices.samples[1:]))

    recovered = XMModule.parse(module(song).to_bytes()).song.voices
    assert isinstance(recovered, InstrumentVoices)
    assert (recovered.samples[0].relative_note, recovered.samples[0].finetune) == (29, -28)
    assert recovered.samples[0].rate == tuned.rate


def test_a_sample_no_key_of_its_instrument_reaches_is_reported(xm_song: Song, xm_voices: InstrumentVoices) -> None:
    # A key is what reaches a sample here, so an instrument counting one no key names holds it in the
    # song's table instead — and a caller about to write the song back is told how many.
    pair = Instrument(
        name="pair",
        keymap=routed_keymap(
            {
                Note(RATE_NOTE): KeyAssignment(sample=0, note=Note(RATE_NOTE)),
                Note(RATE_NOTE + 1): KeyAssignment(sample=1, note=Note(RATE_NOTE + 1)),
            }
        ),
    )
    song = revoiced(xm_song, instruments=(*xm_voices.instruments, pair))
    data = bytearray(module(song).to_bytes())
    offset = instrument_offsets(bytes(data))[-1]
    data[offset + KEYMAP_ORIGIN : offset + KEYMAP_ORIGIN + KEYMAP_NOTES] = bytes(KEYMAP_NOTES)

    with pytest.warns(RepairWarning, match="1 samples no key reaches are held outside this instrument"):
        recovered = XMModule.parse(bytes(data)).song.voices

    assert isinstance(recovered, InstrumentVoices)
    assert recovered.instruments[-1].samples == (len(recovered.samples) - 2,)
    assert len(recovered.samples) == len(xm_voices.samples) + 2


def test_an_instrument_states_its_samples_in_the_order_the_song_holds_them(
    xm_song: Song,
    xm_voices: InstrumentVoices,
) -> None:
    # A keymap reaching a later sample from an earlier key still stores the run in the song's own order,
    # so a module read from this format and written back states its samples where it stated them before.
    crossed = Instrument(
        name="crossed",
        keymap=routed_keymap(
            {
                Note(RATE_NOTE): KeyAssignment(sample=2, note=Note(RATE_NOTE)),
                Note(RATE_NOTE + 1): KeyAssignment(sample=0, note=Note(RATE_NOTE + 1)),
            }
        ),
    )
    song = revoiced(xm_song, instruments=(*xm_voices.instruments, crossed))

    stored = song_groups(song)[-1]
    assert [sample.name for sample in stored.samples] == [xm_voices.samples[0].name, xm_voices.samples[2].name]

    parsed = XMModule.parse(module(song).to_bytes())
    assert XMModule.parse(parsed.to_bytes()).song == parsed.song


def truncated(song: Song, *, drop: int) -> bytes:
    """The module a song writes, with its last bytes taken off — the shape a file cut in transit has."""
    return XMModule.from_song(song, compliance=Compliance.CANONICAL).to_bytes()[:-drop]


def test_a_file_stopping_inside_an_instrument_header_says_so(xm_song: Song) -> None:
    # A record read from bytes the file stops before is zero-filled, so a truncated header states an
    # instrument owning nothing at all. Saying so is what keeps the missing music visible.
    data = XMModule.from_song(xm_song, compliance=Compliance.CANONICAL).to_bytes()
    instrument = instrument_offsets(data)[-1]
    with pytest.warns(RepairWarning, match="a header the file stops inside"):
        XMModule.parse(data[: instrument + 10])


def test_a_file_stopping_inside_a_sample_header_says_so(xm_song: Song) -> None:
    data = XMModule.from_song(xm_song, compliance=Compliance.CANONICAL).to_bytes()
    instrument = instrument_offsets(data)[-1]
    stated = read_int(EMPTY_INSTRUMENT_HEADER.unpack(data[instrument : instrument + 29]), "header_size")
    with pytest.warns(RepairWarning, match="a header the file stops inside"):
        XMModule.parse(data[: instrument + stated + 10])


def test_a_file_stopping_inside_a_waveform_reads_the_frames_it_holds(xm_song: Song) -> None:
    with pytest.warns(RepairWarning, match="read as the .* the file holds"):
        recovered = XMModule.parse(truncated(xm_song, drop=8))

    assert sum(sample.frames for sample in recovered.song.voices.samples) < sum(
        sample.frames for sample in xm_song.voices.samples
    )


def test_a_file_stopping_before_the_instruments_it_states_says_how_many_it_held(xm_song: Song) -> None:
    data = XMModule.from_song(xm_song, compliance=Compliance.CANONICAL).to_bytes()
    with pytest.warns(RepairWarning, match="instruments stated, 0 held"):
        XMModule.parse(data[: instrument_offsets(data)[0]])

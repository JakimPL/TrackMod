import numpy as np
import pytest

from tests.conftest import lattice
from tests.trackers.s3m.conftest import instrument_record
from trackmod.binary.pcm.sign import PcmSign
from trackmod.binary.records.values import RecordValues
from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.sample import Sample
from trackmod.spec.levels import CENTRE_PANNING
from trackmod.spec.pitch import REFERENCE_RATE
from trackmod.trackers.s3m.layout.instrument import INSTRUMENT_RECORD
from trackmod.trackers.s3m.samples.parser import (
    frame_sign,
    parse_sample,
    read_loop,
    stated_frames,
    stored_bytes,
    waveform_start,
)
from trackmod.trackers.s3m.samples.writer import sample_bytes, sample_record
from trackmod.trackers.s3m.spec.flags import RecordType, SampleFlag
from trackmod.trackers.s3m.spec.identity import SIGNED_FRAMES, UNSIGNED_FRAMES
from trackmod.trackers.s3m.spec.sizes import PARAGRAPH_BYTES
from trackmod.trackers.s3m.spec.storage import PCM_SIGN

SILENCE = 0x80
WAVEFORM_PARAGRAPH = bytes(PARAGRAPH_BYTES)


def restored(sample: Sample) -> Sample:
    values = INSTRUMENT_RECORD.unpack(sample_record(sample, data_offset=0))
    return parse_sample(values, sample_bytes(sample), sign=PCM_SIGN, subject="sample 0", repairs=Repairs())


@pytest.mark.parametrize("depth", list(BitDepth))
def test_frames_are_stored_in_the_positive_half_of_their_range(depth: BitDepth) -> None:
    # Frames are shifted a full scale up from where they sound, so silence is the middle of the stored
    # range at either depth rather than zero, and a reader that took them signed would hear them inverted.
    silent = Sample(name="silent", pcm=np.zeros(4), rate=REFERENCE_RATE, depth=depth)
    stored = np.frombuffer(sample_bytes(silent), dtype=f"<u{depth.bytes_per_frame}")
    assert set(stored.tolist()) == {int(depth.scale)}


def test_eight_bit_silence_is_the_byte_at_the_middle_of_the_range() -> None:
    silent = Sample(name="silent", pcm=np.zeros(4), rate=REFERENCE_RATE, depth=BitDepth.EIGHT)
    assert sample_bytes(silent) == bytes([SILENCE] * 4)


@pytest.mark.parametrize("depth", list(BitDepth))
def test_a_waveform_survives_being_written_and_read_back(depth: BitDepth) -> None:
    sample = Sample(
        name="wave",
        pcm=lattice(np.sin(np.linspace(0.0, 6.0, 40)), depth),
        rate=22050,
        depth=depth,
        volume=48,
    )
    recovered = restored(sample)
    assert recovered == sample
    assert np.array_equal(recovered.pcm, sample.pcm)


def test_a_stereo_waveform_stores_each_channel_in_full_before_the_next() -> None:
    left = lattice(np.linspace(-1.0, 1.0, 16), BitDepth.EIGHT)
    right = lattice(np.linspace(1.0, -1.0, 16), BitDepth.EIGHT)
    sample = Sample(
        name="wide",
        pcm=np.stack([left, right], axis=1),
        rate=REFERENCE_RATE,
        depth=BitDepth.EIGHT,
    )
    stored = sample_bytes(sample)
    assert stored[:16] != stored[16:]
    assert np.array_equal(restored(sample).pcm, sample.pcm)


def test_a_looping_sample_states_both_ends_in_frames() -> None:
    sample = Sample(
        name="looped",
        pcm=lattice(np.linspace(-1.0, 1.0, 48)),
        rate=REFERENCE_RATE,
        loop=Loop(begin=8, end=40, mode=LoopMode.FORWARD),
    )
    values = INSTRUMENT_RECORD.unpack(sample_record(sample, data_offset=0))
    assert values["loop_begin"] == 8
    assert values["loop_end"] == 40
    assert SampleFlag(int(values["flags"])) & SampleFlag.LOOP
    assert restored(sample).loop == sample.loop


def test_a_slot_holding_no_frames_states_so_and_keeps_what_it_was_reserved_with() -> None:
    placeholder = Sample(
        name="reserved",
        pcm=np.zeros(0),
        rate=22050,
        depth=BitDepth.EIGHT,
        volume=63,
        filename="RESERVED.SMP",
    )
    values = INSTRUMENT_RECORD.unpack(sample_record(placeholder, data_offset=0))
    assert values["type"] == int(RecordType.EMPTY)
    assert restored(placeholder) == placeholder


def test_a_record_stating_more_than_full_reads_as_full() -> None:
    values = INSTRUMENT_RECORD.unpack(instrument_record(length=4, volume=200))
    repairs = Repairs()
    assert parse_sample(values, bytes(4), sign=PCM_SIGN, subject="sample 0", repairs=repairs).volume == 64
    assert [repair for _, repair in repairs.entries] == ["volume 200 read as 64"]


def test_a_record_describing_an_opl_patch_is_refused_by_name() -> None:
    values = INSTRUMENT_RECORD.unpack(instrument_record(kind=int(RecordType.ADLIB_SNARE)))
    with pytest.raises(ValueError, match="adlib_snare"):
        parse_sample(values, b"", sign=PCM_SIGN, subject="sample 3", repairs=Repairs())


def test_a_record_stating_a_packing_is_refused() -> None:
    values = INSTRUMENT_RECORD.unpack(instrument_record(length=4, pack=1))
    with pytest.raises(ValueError, match="packing 1"):
        parse_sample(values, bytes(4), sign=PCM_SIGN, subject="sample 0", repairs=Repairs())


def test_a_loop_reaching_past_the_frames_stored_is_drawn_back_inside_them() -> None:
    values = INSTRUMENT_RECORD.unpack(
        instrument_record(length=8, loop_begin=2, loop_end=64, flags=int(SampleFlag.LOOP))
    )
    repairs = Repairs()
    sample = parse_sample(values, bytes(8), sign=PCM_SIGN, subject="sample 0", repairs=repairs)
    assert sample.loop == Loop(begin=2, end=8, mode=LoopMode.FORWARD)
    assert repairs.entries


def test_a_rate_of_zero_reads_as_the_rate_this_lineage_measures_middle_c_by() -> None:
    values = INSTRUMENT_RECORD.unpack(instrument_record(length=4, c2spd=0))
    repairs = Repairs()
    assert parse_sample(values, bytes(4), sign=PCM_SIGN, subject="sample 0", repairs=repairs).rate == REFERENCE_RATE
    assert repairs.entries


def test_a_record_states_how_many_bytes_its_waveform_takes_across_every_channel() -> None:
    both = int(SampleFlag.STEREO | SampleFlag.SIXTEEN_BIT)
    assert stored_bytes(INSTRUMENT_RECORD.unpack(instrument_record(length=10, flags=both))) == 40
    assert stored_bytes(INSTRUMENT_RECORD.unpack(instrument_record(length=10))) == 10


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("panning", CENTRE_PANNING, "pans by channel"),
        ("sustain_loop", Loop(begin=0, end=8, mode=LoopMode.FORWARD), "sustain loop"),
        ("loop", Loop(begin=0, end=8, mode=LoopMode.PING_PONG), "loops forwards"),
    ],
)
def test_a_sample_this_format_keeps_no_field_for_is_refused(field: str, value: object, message: str) -> None:
    sample = Sample(name="odd", pcm=np.zeros(16), rate=REFERENCE_RATE, **{field: value})
    with pytest.raises(ValueError, match=message):
        sample_record(sample, data_offset=0)


def test_a_waveform_the_file_stops_inside_reads_as_the_frames_it_holds() -> None:
    values = INSTRUMENT_RECORD.unpack(instrument_record(length=64, paragraph=1))
    repairs = Repairs()
    sample = parse_sample(
        values, stated_frames(values, bytes(16 + 8)), sign=PCM_SIGN, subject="sample 0", repairs=repairs
    )
    assert sample.frames == 8
    assert [repair for _, repair in repairs.entries] == ["waveform of 64 frames read as the 8 the file holds"]


def test_a_record_opening_with_a_byte_naming_no_kind_is_refused() -> None:
    values = INSTRUMENT_RECORD.unpack(instrument_record(kind=200))
    with pytest.raises(ValueError, match="names none of the records"):
        parse_sample(values, b"", sign=PCM_SIGN, subject="sample 7", repairs=Repairs())


def test_a_module_from_the_first_release_states_its_frames_are_signed() -> None:
    # Scream Tracker 3 wrote signed frames in its first release and unsigned ones after it, and the
    # header says which, so a reader follows the header.
    assert frame_sign(SIGNED_FRAMES) is PcmSign.SIGNED
    assert frame_sign(UNSIGNED_FRAMES) is PcmSign.UNSIGNED

    values = INSTRUMENT_RECORD.unpack(instrument_record(length=4))
    signed = parse_sample(values, bytes([0x80] * 4), sign=PcmSign.SIGNED, subject="a", repairs=Repairs())
    unsigned = parse_sample(values, bytes([0x80] * 4), sign=PCM_SIGN, subject="b", repairs=Repairs())
    assert np.allclose(signed.pcm, -1.0)
    assert np.allclose(unsigned.pcm, 0.0)


def held_sample(values: RecordValues, held: bytes, *, repairs: Repairs) -> Sample:
    """The sample a record reads as, given the bytes a file holds from the paragraph it points at."""
    return parse_sample(
        values, stated_frames(values, WAVEFORM_PARAGRAPH + held), sign=PCM_SIGN, subject="sample 0", repairs=repairs
    )


def test_a_sixteen_bit_waveform_the_file_stops_inside_a_frame_of_reads_whole_frames() -> None:
    values = INSTRUMENT_RECORD.unpack(instrument_record(length=8, flags=int(SampleFlag.SIXTEEN_BIT), paragraph=1))
    repairs = Repairs()
    sample = held_sample(values, bytes(9), repairs=repairs)
    assert sample.frames == 4
    assert [repair for _, repair in repairs.entries] == ["waveform of 8 frames read as the 4 the file holds"]


def test_a_stereo_waveform_the_file_stops_inside_reads_as_far_as_both_channels_reach() -> None:
    # Each channel is stored in full, the left before the right, so a block cut short holds all of the
    # left and a part of the right. A frame is the pair a player sounds together, so the two are read
    # to the length they share and every frame keeps the amplitudes that belong to it.
    values = INSTRUMENT_RECORD.unpack(instrument_record(length=8, flags=int(SampleFlag.STEREO), paragraph=1))
    left, right = bytes(range(0x80, 0x88)), bytes(range(0x7F, 0x7B, -1))
    repairs = Repairs()
    sample = held_sample(values, left + right, repairs=repairs)
    assert sample.channels == 2
    assert sample.frames == 4
    assert [repair for _, repair in repairs.entries] == ["waveform of 8 frames read as the 4 the file holds"]

    whole = INSTRUMENT_RECORD.unpack(instrument_record(length=4, flags=int(SampleFlag.STEREO), paragraph=1))
    paired = held_sample(whole, left[:4] + right, repairs=Repairs())
    assert np.array_equal(sample.pcm, paired.pcm)


def test_a_loop_whose_ends_meet_repeats_nothing_and_is_reported() -> None:
    values = INSTRUMENT_RECORD.unpack(
        instrument_record(length=8, flags=int(SampleFlag.LOOP), loop_begin=4, loop_end=4, paragraph=1)
    )
    repairs = Repairs()
    assert read_loop(values, subject="sample 0", repairs=repairs) is None
    assert held_sample(values, bytes(8), repairs=Repairs()).loop is None
    assert [repair for _, repair in repairs.entries] == ["loop 4..4 spans no frame and reads as none"]


def test_a_record_reaches_a_waveform_past_the_megabyte_two_pointer_bytes_see() -> None:
    # Two bytes name a paragraph one megabyte into a file. A record spends a third byte above them on
    # its waveform alone, which is what lets a sample sit anywhere in a file sixteen times that long.
    paragraph = 0x012345
    values = INSTRUMENT_RECORD.unpack(instrument_record(paragraph=paragraph, length=4))
    assert waveform_start(values) == paragraph * PARAGRAPH_BYTES

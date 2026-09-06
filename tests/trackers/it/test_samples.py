import numpy as np

from tests.trackers.it.conftest import stated
from trackmod.binary.pcm.encoding import PcmEncoding
from trackmod.binary.pcm.quantise import dequantise
from trackmod.binary.pcm.sign import PcmSign
from trackmod.binary.records.values import RecordValues
from trackmod.core.repairs.report import Repairs
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.sample import Sample
from trackmod.core.samples.vibrato import Vibrato
from trackmod.trackers.it.layout.sample import SAMPLE_HEADER
from trackmod.trackers.it.samples.parser import (
    parse_sample,
    stored_channels,
    stored_convert,
    stored_encoding,
    stored_end,
    stored_frames,
    stored_pcm,
    stored_sign,
)
from trackmod.trackers.it.samples.writer import sample_bytes, sample_header
from trackmod.trackers.it.spec.flags import SampleConvert, SampleFlag

RATE = 44100


SUBJECT = "sample 0"


def _values(
    *,
    flags: SampleFlag,
    length: int,
    convert: SampleConvert = SampleConvert.SIGNED,
    sample_pointer: int = 0,
) -> RecordValues:
    return {
        "flags": int(flags),
        "length": length,
        "convert": int(convert),
        "sample_pointer": sample_pointer,
    }


def _convert(values: RecordValues) -> SampleConvert:
    return stored_convert(values, subject=SUBJECT, repairs=Repairs())


def test_stored_channels_reads_the_stereo_flag() -> None:
    assert stored_channels(_values(flags=SampleFlag.DATA, length=1)) == 1
    assert stored_channels(_values(flags=SampleFlag.DATA | SampleFlag.STEREO, length=1)) == 2


def test_stored_frames_counts_bytes_across_every_channel() -> None:
    mono = _values(flags=SampleFlag.DATA | SampleFlag.SIXTEEN_BIT, length=10)
    stereo = _values(flags=SampleFlag.DATA | SampleFlag.SIXTEEN_BIT | SampleFlag.STEREO, length=10)
    assert stored_frames(mono) == 20
    assert stored_frames(stereo) == 40


def test_an_uncompressed_stereo_sample_round_trips_through_the_header_and_writer() -> None:
    left = np.linspace(-1.0, 1.0, 16)
    right = np.linspace(1.0, -1.0, 16)
    sample = Sample(name="stereo", pcm=np.stack([left, right], axis=1), rate=RATE)

    header = sample_header(sample, data_offset=0)
    values = SAMPLE_HEADER.unpack(header)
    recovered = parse_sample(values, sample_bytes(sample), subject="sample", repairs=Repairs())

    assert recovered.channels == 2
    assert recovered.frames == 16
    assert np.allclose(recovered.pcm, sample.pcm, atol=1.5 / sample.depth.scale)


def test_filename_and_vibrato_round_trip_through_the_header() -> None:
    vibrato = Vibrato(speed=4, depth=8, rate=16, waveform=1)
    sample = Sample(name="s", pcm=np.zeros(4), rate=RATE, filename="DRUM.WAV", vibrato=vibrato)

    header = sample_header(sample, data_offset=0)
    values = SAMPLE_HEADER.unpack(header)
    recovered = parse_sample(values, sample_bytes(sample), subject="sample", repairs=Repairs())

    assert recovered.filename == "DRUM.WAV"
    assert recovered.vibrato == vibrato


def test_a_compressed_stereo_sample_is_decoded_as_two_independent_streams() -> None:
    depth = BitDepth.SIXTEEN
    left_differences = [10, -3, 5, 0, -12]
    right_differences = [1, 1, -2, 4, 0]
    data = stated(left_differences, depth=depth) + stated(right_differences, depth=depth)
    values = _values(
        flags=SampleFlag.DATA | SampleFlag.SIXTEEN_BIT | SampleFlag.STEREO | SampleFlag.COMPRESSED,
        length=len(left_differences),
    )

    pcm = stored_pcm(values, data, depth=depth, subject=SUBJECT, repairs=Repairs())

    assert pcm.shape == (5, 2)
    assert np.allclose(pcm[:, 0], dequantise(np.cumsum(left_differences), depth))
    assert np.allclose(pcm[:, 1], dequantise(np.cumsum(right_differences), depth))


def test_stored_end_sums_both_channels_of_a_compressed_stereo_sample() -> None:
    depth = BitDepth.EIGHT
    data = stated([1, 2, 3], depth=depth) + stated([4, 5, 6], depth=depth)
    values = _values(flags=SampleFlag.DATA | SampleFlag.STEREO | SampleFlag.COMPRESSED, length=3)

    assert stored_end(values, data) == len(data)


def test_a_compressed_mono_sample_is_decoded() -> None:
    depth = BitDepth.EIGHT
    differences = [1, 2, 3]
    data = stated(differences, depth=depth)
    values = _values(flags=SampleFlag.DATA | SampleFlag.COMPRESSED, length=len(differences))

    pcm = stored_pcm(values, data, depth=depth, subject=SUBJECT, repairs=Repairs())

    assert pcm.shape == (3,)
    assert np.allclose(pcm, dequantise(np.cumsum(differences), depth))


def test_stored_end_reads_a_single_channel_of_a_compressed_mono_sample() -> None:
    depth = BitDepth.EIGHT
    data = stated([1, 2, 3], depth=depth)
    values = _values(flags=SampleFlag.DATA | SampleFlag.COMPRESSED, length=3)

    assert stored_end(values, data) == len(data)


def test_a_header_stating_unsigned_frames_reads_them_centred_on_silence() -> None:
    # Scream Tracker 3 wrote every waveform this way, and this header can state it too: 0x80 is silence.
    depth = BitDepth.EIGHT
    data = bytes([0x80, 0xC0, 0x40, 0xFF, 0x00])
    values = _values(flags=SampleFlag.DATA, length=len(data), convert=SampleConvert(0))

    assert stored_sign(_convert(values)) is PcmSign.UNSIGNED
    pcm = stored_pcm(values, data, depth=depth, subject=SUBJECT, repairs=Repairs())

    assert np.allclose(pcm, dequantise(np.asarray([0, 64, -64, 127, -128]), depth))


def test_a_header_stating_signed_frames_reads_them_where_they_sit() -> None:
    depth = BitDepth.EIGHT
    data = bytes([0x00, 0x40, 0xC0, 0x7F, 0x80])
    values = _values(flags=SampleFlag.DATA, length=len(data))

    assert stored_sign(_convert(values)) is PcmSign.SIGNED
    pcm = stored_pcm(values, data, depth=depth, subject=SUBJECT, repairs=Repairs())

    assert np.allclose(pcm, dequantise(np.asarray([0, 64, -64, 127, -128]), depth))


def test_a_header_stating_raw_differences_reads_them_as_a_running_sum() -> None:
    depth = BitDepth.EIGHT
    differences = [10, 5, -3, 20]
    data = bytes(value & 0xFF for value in differences)
    values = _values(
        flags=SampleFlag.DATA,
        length=len(differences),
        convert=SampleConvert.SIGNED | SampleConvert.DELTA,
    )

    assert stored_encoding(_convert(values)) is PcmEncoding.DELTA
    pcm = stored_pcm(values, data, depth=depth, subject=SUBJECT, repairs=Repairs())

    assert np.allclose(pcm, dequantise(np.cumsum(differences), depth))


def test_a_compressed_header_stating_differences_sums_its_blocks_twice() -> None:
    # The one convert bit is read against how the frames are stored, so a compressed block sums twice.
    depth = BitDepth.EIGHT
    differences = [1, 2, 3, 4]
    data = stated(differences, depth=depth)
    values = _values(
        flags=SampleFlag.DATA | SampleFlag.COMPRESSED,
        length=len(differences),
        convert=SampleConvert.SIGNED | SampleConvert.DELTA,
    )

    pcm = stored_pcm(values, data, depth=depth, subject=SUBJECT, repairs=Repairs())

    assert np.allclose(pcm, dequantise(np.cumsum(np.cumsum(differences)), depth))


def test_a_written_header_states_the_signed_amplitudes_the_writer_stores() -> None:
    sample = Sample(name="s", pcm=np.linspace(-1.0, 1.0, 8), rate=RATE)
    values = SAMPLE_HEADER.unpack(sample_header(sample, data_offset=0))

    assert stored_sign(_convert(values)) is PcmSign.SIGNED
    assert stored_encoding(_convert(values)) is PcmEncoding.ABSOLUTE


def test_a_convert_byte_naming_a_storage_this_reader_leaves_out_reads_signed_amplitudes() -> None:
    # A byte of 0xFF claims big-endian frames, ADPCM and a synthesiser's own waveform all at once.
    depth = BitDepth.EIGHT
    data = bytes([0x00, 0x40, 0xC0, 0x7F, 0x80])
    values = _values(flags=SampleFlag.DATA, length=len(data), convert=SampleConvert(0xFF))
    repairs = Repairs()

    pcm = stored_pcm(values, data, depth=depth, subject=SUBJECT, repairs=repairs)

    assert np.allclose(pcm, dequantise(np.asarray([0, 64, -64, 127, -128]), depth))
    assert repairs.entries == ((SUBJECT, "a convert byte of 0xff reads as signed amplitudes"),)


def test_a_sixteen_bit_waveform_the_file_stops_inside_a_frame_of_reads_whole_frames() -> None:
    sample = Sample(name="wave", pcm=np.linspace(-1.0, 1.0, 8), rate=RATE)
    values = SAMPLE_HEADER.unpack(sample_header(sample, data_offset=0))
    repairs = Repairs()

    recovered = parse_sample(values, sample_bytes(sample)[:9], subject=SUBJECT, repairs=repairs)

    assert recovered.frames == 4
    assert repairs.entries == ((SUBJECT, "waveform of 8 frames read as the 4 the file holds"),)


def test_a_stereo_waveform_the_file_stops_inside_reads_as_far_as_both_channels_reach() -> None:
    # Each channel is stored in full, the left before the right, so a block cut short holds all of the
    # left and a part of the right. A frame is the pair a player sounds together, so the two are read
    # to the length they share and every frame keeps the amplitudes that belong to it.
    pcm = np.stack([np.linspace(-1.0, 1.0, 8), np.linspace(1.0, -1.0, 8)], axis=1)
    sample = Sample(name="wide", pcm=pcm, rate=RATE)
    values = SAMPLE_HEADER.unpack(sample_header(sample, data_offset=0))
    channel_bytes = sample.frames * sample.depth.bytes_per_frame
    repairs = Repairs()

    recovered = parse_sample(
        values,
        sample_bytes(sample)[: channel_bytes + channel_bytes // 2],
        subject=SUBJECT,
        repairs=repairs,
    )

    assert recovered.channels == 2
    assert recovered.frames == 4
    assert np.allclose(recovered.pcm, pcm[:4], atol=1.5 / sample.depth.scale)
    assert repairs.entries == ((SUBJECT, "waveform of 8 frames read as the 4 the file holds"),)

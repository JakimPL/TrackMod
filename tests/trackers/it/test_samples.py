import numpy as np

from tests.trackers.it.conftest import stated
from trackmod.binary.pcm.quantise import dequantise
from trackmod.binary.records.values import RecordValues
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.sample import Sample
from trackmod.core.samples.vibrato import Vibrato
from trackmod.trackers.it.layout.sample import SAMPLE_HEADER
from trackmod.trackers.it.samples.parser import (
    parse_sample,
    stored_channels,
    stored_end,
    stored_frames,
    stored_pcm,
)
from trackmod.trackers.it.samples.writer import sample_bytes, sample_header
from trackmod.trackers.it.spec.flags import SampleFlag

RATE = 44100


def _values(*, flags: SampleFlag, length: int, sample_pointer: int = 0) -> RecordValues:
    return {"flags": int(flags), "length": length, "sample_pointer": sample_pointer}


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
    recovered = parse_sample(values, sample_bytes(sample), doubled=False)

    assert recovered.channels == 2
    assert recovered.frames == 16
    assert np.allclose(recovered.pcm, sample.pcm, atol=1.5 / sample.depth.scale)


def test_filename_and_vibrato_round_trip_through_the_header() -> None:
    vibrato = Vibrato(speed=4, depth=8, rate=16, waveform=1)
    sample = Sample(name="s", pcm=np.zeros(4), rate=RATE, filename="DRUM.WAV", vibrato=vibrato)

    header = sample_header(sample, data_offset=0)
    values = SAMPLE_HEADER.unpack(header)
    recovered = parse_sample(values, sample_bytes(sample), doubled=False)

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

    pcm = stored_pcm(values, data, depth=depth, doubled=False)

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

    pcm = stored_pcm(values, data, depth=depth, doubled=False)

    assert pcm.shape == (3,)
    assert np.allclose(pcm, dequantise(np.cumsum(differences), depth))


def test_stored_end_reads_a_single_channel_of_a_compressed_mono_sample() -> None:
    depth = BitDepth.EIGHT
    data = stated([1, 2, 3], depth=depth)
    values = _values(flags=SampleFlag.DATA | SampleFlag.COMPRESSED, length=3)

    assert stored_end(values, data) == len(data)

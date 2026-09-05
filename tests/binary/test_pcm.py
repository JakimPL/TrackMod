from typing import Final

import numpy as np
import pytest
from numpy.typing import NDArray

from trackmod.binary.pcm.codec import decode_pcm, encode_pcm
from trackmod.binary.pcm.encoding import PcmEncoding
from trackmod.binary.pcm.quantise import quantise
from trackmod.binary.pcm.sign import NO_BIAS, PcmSign, bias, dtype_for
from trackmod.core.samples.depth import BitDepth

DEPTHS = list(BitDepth)
ENCODINGS = list(PcmEncoding)
SIGNS = list(PcmSign)

GOLDEN_PCM: Final = np.asarray([0.0, 0.5, -0.5, 1.0, -1.0])
GOLDEN_BYTES: Final[dict[tuple[BitDepth, PcmEncoding, PcmSign], bytes]] = {
    (BitDepth.EIGHT, PcmEncoding.ABSOLUTE, PcmSign.SIGNED): bytes.fromhex("0040c07f80"),
    (BitDepth.EIGHT, PcmEncoding.ABSOLUTE, PcmSign.UNSIGNED): bytes.fromhex("80c040ff00"),
    (BitDepth.EIGHT, PcmEncoding.DELTA, PcmSign.SIGNED): bytes.fromhex("004080bf01"),
    (BitDepth.EIGHT, PcmEncoding.DELTA, PcmSign.UNSIGNED): bytes.fromhex("804080bf01"),
    (BitDepth.SIXTEEN, PcmEncoding.ABSOLUTE, PcmSign.SIGNED): bytes.fromhex("0000004000c0ff7f0080"),
    (BitDepth.SIXTEEN, PcmEncoding.ABSOLUTE, PcmSign.UNSIGNED): bytes.fromhex("008000c00040ffff0000"),
    (BitDepth.SIXTEEN, PcmEncoding.DELTA, PcmSign.SIGNED): bytes.fromhex("000000400080ffbf0100"),
    (BitDepth.SIXTEEN, PcmEncoding.DELTA, PcmSign.UNSIGNED): bytes.fromhex("008000400080ffbf0100"),
}


@pytest.fixture
def waveform() -> NDArray[np.float64]:
    """A sine plus a full-scale ramp — the ramp is the worst case for delta storage."""
    time = np.linspace(0.0, 1.0, 512, endpoint=False)
    return np.concatenate([np.sin(2 * np.pi * 4 * time), np.linspace(-1.0, 1.0, 512, endpoint=False)])


@pytest.mark.parametrize("depth", DEPTHS, ids=lambda depth: f"{depth}bit")
@pytest.mark.parametrize("encoding", ENCODINGS, ids=lambda encoding: str(encoding))
@pytest.mark.parametrize("sign", SIGNS, ids=lambda sign: str(sign))
def test_stored_frames_read_back_within_one_quantisation_step(
    waveform: NDArray[np.float64], depth: BitDepth, encoding: PcmEncoding, sign: PcmSign
) -> None:
    stored = encode_pcm(waveform, depth=depth, encoding=encoding, sign=sign)
    recovered = decode_pcm(stored, depth=depth, encoding=encoding, sign=sign)
    assert np.max(np.abs(recovered - waveform)) <= 1.5 / depth.scale


@pytest.mark.parametrize("depth", DEPTHS, ids=lambda depth: f"{depth}bit")
@pytest.mark.parametrize("encoding", ENCODINGS, ids=lambda encoding: str(encoding))
@pytest.mark.parametrize("sign", SIGNS, ids=lambda sign: str(sign))
def test_stored_size_is_one_frame_per_sample(
    waveform: NDArray[np.float64], depth: BitDepth, encoding: PcmEncoding, sign: PcmSign
) -> None:
    stored = encode_pcm(waveform, depth=depth, encoding=encoding, sign=sign)
    assert len(stored) == waveform.size * depth.bytes_per_frame


@pytest.mark.parametrize(("axes", "expected"), sorted(GOLDEN_BYTES.items(), key=str), ids=str)
def test_the_stored_bytes_are_the_ones_pinned_here(
    axes: tuple[BitDepth, PcmEncoding, PcmSign], expected: bytes
) -> None:
    # Both formats that already read and write PCM store signed frames, so the signed rows here are
    # exactly what this library wrote before the signedness axis existed.
    depth, encoding, sign = axes
    assert encode_pcm(GOLDEN_PCM, depth=depth, encoding=encoding, sign=sign) == expected


@pytest.mark.parametrize("depth", DEPTHS, ids=lambda depth: f"{depth}bit")
def test_signed_storage_leaves_an_amplitude_where_it_sits(depth: BitDepth) -> None:
    assert bias(depth, sign=PcmSign.SIGNED) == NO_BIAS
    assert dtype_for(depth, sign=PcmSign.SIGNED) == f"<i{depth.bytes_per_frame}"


@pytest.mark.parametrize("depth", DEPTHS, ids=lambda depth: f"{depth}bit")
def test_unsigned_storage_shifts_an_amplitude_to_the_middle_of_the_range(depth: BitDepth) -> None:
    assert bias(depth, sign=PcmSign.UNSIGNED) == depth.scale
    assert dtype_for(depth, sign=PcmSign.UNSIGNED) == f"<u{depth.bytes_per_frame}"

    silence = encode_pcm(np.zeros(4), depth=depth, encoding=PcmEncoding.ABSOLUTE, sign=PcmSign.UNSIGNED)
    stored = np.frombuffer(silence, dtype=dtype_for(depth, sign=PcmSign.UNSIGNED))
    assert np.all(stored == depth.scale)


@pytest.mark.parametrize("depth", DEPTHS, ids=lambda depth: f"{depth}bit")
def test_the_two_signs_store_the_same_waveform_a_bias_apart(waveform: NDArray[np.float64], depth: BitDepth) -> None:
    signed = encode_pcm(waveform, depth=depth, encoding=PcmEncoding.ABSOLUTE, sign=PcmSign.SIGNED)
    unsigned = encode_pcm(waveform, depth=depth, encoding=PcmEncoding.ABSOLUTE, sign=PcmSign.UNSIGNED)
    here = np.frombuffer(signed, dtype=dtype_for(depth, sign=PcmSign.SIGNED)).astype(np.int64)
    there = np.frombuffer(unsigned, dtype=dtype_for(depth, sign=PcmSign.UNSIGNED)).astype(np.int64)
    assert np.all(there - here == bias(depth, sign=PcmSign.UNSIGNED))


@pytest.mark.parametrize("depth", DEPTHS, ids=lambda depth: f"{depth}bit")
def test_reading_unsigned_frames_as_signed_ones_shifts_the_waveform_by_full_scale(depth: BitDepth) -> None:
    # This is what a reader trusting its format over the record it reads hears, and why the axis exists.
    quiet = np.full(8, 0.25)
    stored = encode_pcm(quiet, depth=depth, encoding=PcmEncoding.ABSOLUTE, sign=PcmSign.UNSIGNED)
    misread = decode_pcm(stored, depth=depth, encoding=PcmEncoding.ABSOLUTE, sign=PcmSign.SIGNED)
    assert np.allclose(misread, quiet - 1.0)


@pytest.mark.parametrize("depth", DEPTHS, ids=lambda depth: f"{depth}bit")
def test_the_first_delta_is_the_first_stored_amplitude(depth: BitDepth) -> None:
    # Taking the first difference against zero is what keeps a delta-stored waveform free of a DC step.
    pcm = np.asarray([0.5, 0.5, 0.5])
    stored = encode_pcm(pcm, depth=depth, encoding=PcmEncoding.DELTA, sign=PcmSign.SIGNED)
    delta = np.frombuffer(stored, dtype=dtype_for(depth, sign=PcmSign.SIGNED))
    assert delta[0] == quantise(pcm, depth)[0]
    assert np.all(delta[1:] == 0)


@pytest.mark.parametrize("depth", DEPTHS, ids=lambda depth: f"{depth}bit")
@pytest.mark.parametrize("sign", SIGNS, ids=lambda sign: str(sign))
def test_a_delta_that_overshoots_the_stored_width_wraps_back_on_the_running_sum(depth: BitDepth, sign: PcmSign) -> None:
    swing = np.asarray([-1.0, 1.0, -1.0, 1.0])
    stored = encode_pcm(swing, depth=depth, encoding=PcmEncoding.DELTA, sign=sign)
    recovered = decode_pcm(stored, depth=depth, encoding=PcmEncoding.DELTA, sign=sign)
    assert np.max(np.abs(recovered - swing)) <= 1.5 / depth.scale


@pytest.mark.parametrize("depth", DEPTHS, ids=lambda depth: f"{depth}bit")
def test_quantisation_saturates_at_the_signed_range(depth: BitDepth) -> None:
    quantised = quantise(np.asarray([-2.0, -1.0, 0.0, 1.0, 2.0]), depth)
    assert quantised.min() == -depth.scale
    assert quantised.max() == depth.scale - 1

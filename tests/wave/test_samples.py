from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from trackmod.binary.pcm.quantise import dequantise, quantise
from trackmod.binary.records.values import read_int
from trackmod.core.samples.depth import BitDepth
from trackmod.core.samples.loop import Loop, LoopMode
from trackmod.core.samples.sample import STEREO_CHANNELS, Sample
from trackmod.core.samples.vibrato import NO_VIBRATO, Vibrato
from trackmod.spec.levels import MAX_VOLUME
from trackmod.spec.pitch import RATE_NOTE
from trackmod.wave.chunks import tagged, unwrapped, wrapped
from trackmod.wave.layout import FORMAT_CHUNK, SAMPLER_CHUNK, SAMPLER_LOOP
from trackmod.wave.parser import load_sample, parse_sample
from trackmod.wave.spec import (
    DATA_TAG,
    FORMAT_TAG,
    INTEGER_SAMPLES,
    NANOSECONDS,
    PING_PONG_LOOP,
    SAMPLER_CHUNK_BYTES,
    SAMPLER_TAG,
)
from trackmod.wave.writer import save_sample, write_sample

RATE = 22050
FRAMES = 64

DEPTHS = list(BitDepth)
CHANNEL_COUNTS = [1, STEREO_CHANNELS]


def stored(values: NDArray[np.float64], depth: BitDepth) -> NDArray[np.float64]:
    """A waveform pulled onto the integer lattice its depth stores, so storing it changes nothing."""
    return dequantise(quantise(values, depth), depth)


def waveform(*, channels: int = 1, depth: BitDepth = BitDepth.SIXTEEN, seed: int = 1) -> NDArray[np.float64]:
    rng = np.random.default_rng(seed)
    shape = (FRAMES,) if channels == 1 else (FRAMES, channels)
    return stored(rng.uniform(-1.0, 1.0, shape), depth)


def make_sample(
    *,
    channels: int = 1,
    depth: BitDepth = BitDepth.SIXTEEN,
    volume: int = MAX_VOLUME,
    gain: int = MAX_VOLUME,
    panning: int | None = None,
    filename: str = "",
    vibrato: Vibrato = NO_VIBRATO,
    loop: Loop | None = None,
    sustain_loop: Loop | None = None,
) -> Sample:
    return Sample(
        name="lead",
        pcm=waveform(channels=channels, depth=depth),
        rate=RATE,
        depth=depth,
        volume=volume,
        gain=gain,
        panning=panning,
        filename=filename,
        vibrato=vibrato,
        loop=loop,
        sustain_loop=sustain_loop,
    )


def sampler_chunk(sample: Sample) -> bytes:
    return unwrapped(write_sample(sample))[SAMPLER_TAG]


@pytest.mark.parametrize("depth", DEPTHS, ids=lambda depth: f"{depth}bit")
@pytest.mark.parametrize("channels", CHANNEL_COUNTS, ids=lambda channels: f"{channels}ch")
def test_a_written_waveform_reads_back_as_the_one_it_came_from(depth: BitDepth, channels: int) -> None:
    sample = make_sample(channels=channels, depth=depth)
    assert parse_sample(write_sample(sample)) == sample


def test_every_setting_a_tracker_sounds_a_sample_with_arrives_back() -> None:
    sample = make_sample(
        volume=48,
        gain=52,
        panning=200,
        filename="LEAD.ITS",
        vibrato=Vibrato(speed=5, depth=6, rate=7, waveform=1),
        loop=Loop(begin=8, end=48),
        sustain_loop=Loop(begin=2, end=20, mode=LoopMode.PING_PONG),
    )
    assert parse_sample(write_sample(sample)) == sample


@pytest.mark.parametrize("mode", list(LoopMode), ids=lambda mode: str(mode))
def test_a_loop_reads_back_over_the_frames_it_repeated(mode: LoopMode) -> None:
    sample = make_sample(loop=Loop(begin=8, end=48, mode=mode))
    assert parse_sample(write_sample(sample)).loop == sample.loop


def test_a_loop_reaching_the_last_frame_reads_back_over_the_whole_waveform() -> None:
    sample = make_sample(loop=Loop(begin=0, end=FRAMES))
    assert parse_sample(write_sample(sample)).loop == Loop(begin=0, end=FRAMES)


def test_a_stored_loop_end_names_the_last_frame_it_plays() -> None:
    # RIFF loop ends are inclusive where the model's are one past the last frame, so the stored end
    # sits one below -- the single fact a reader of these files has to agree on.
    values = SAMPLER_LOOP.unpack_at(sampler_chunk(make_sample(loop=Loop(begin=8, end=48))), SAMPLER_CHUNK_BYTES)
    assert (read_int(values, "begin"), read_int(values, "end")) == (8, 47)


def test_a_ping_pong_loop_states_the_mode_that_turns_it_around() -> None:
    payload = sampler_chunk(make_sample(loop=Loop(begin=8, end=48, mode=LoopMode.PING_PONG)))
    assert read_int(SAMPLER_LOOP.unpack_at(payload, SAMPLER_CHUNK_BYTES), "mode") == PING_PONG_LOOP


def test_a_sustain_loop_is_stated_before_the_ordinary_one() -> None:
    sample = make_sample(loop=Loop(begin=8, end=48), sustain_loop=Loop(begin=2, end=20))
    payload = sampler_chunk(sample)
    assert read_int(SAMPLER_CHUNK.unpack_at(payload, 0), "loops") == 2
    assert read_int(SAMPLER_LOOP.unpack_at(payload, SAMPLER_CHUNK_BYTES), "begin") == 2


def test_a_sample_looping_only_over_its_sustain_still_states_a_pair() -> None:
    # Order is all that tells the two apart, so the sustain loop stays first of two records and the
    # second spans nothing.
    sample = make_sample(sustain_loop=Loop(begin=2, end=20))
    assert read_int(SAMPLER_CHUNK.unpack_at(sampler_chunk(sample), 0), "loops") == 2

    read = parse_sample(write_sample(sample))
    assert read.sustain_loop == sample.sustain_loop
    assert read.loop is None


def test_the_file_states_the_pitch_the_waveform_sounds_unaltered() -> None:
    values = SAMPLER_CHUNK.unpack_at(sampler_chunk(make_sample()), 0)
    assert read_int(values, "base_note") == RATE_NOTE
    assert read_int(values, "period") == NANOSECONDS // RATE


@pytest.mark.parametrize("depth", DEPTHS, ids=lambda depth: f"{depth}bit")
@pytest.mark.parametrize("channels", CHANNEL_COUNTS, ids=lambda channels: f"{channels}ch")
def test_the_format_chunk_states_how_wide_a_frame_is_and_how_fast_they_go_by(depth: BitDepth, channels: int) -> None:
    sample = make_sample(channels=channels, depth=depth)
    values = FORMAT_CHUNK.unpack_at(unwrapped(write_sample(sample))[FORMAT_TAG], 0)
    block = channels * depth.bytes_per_frame
    assert read_int(values, "encoding") == INTEGER_SAMPLES
    assert read_int(values, "channels") == channels
    assert read_int(values, "bits") == int(depth)
    assert read_int(values, "block_align") == block
    assert read_int(values, "byte_rate") == RATE * block


def test_a_stereo_waveform_stores_one_frame_of_each_channel_in_turn() -> None:
    sample = make_sample(channels=STEREO_CHANNELS, depth=BitDepth.EIGHT)
    frames = np.frombuffer(unwrapped(write_sample(sample))[DATA_TAG], dtype="<u1")
    assert frames.size == FRAMES * STEREO_CHANNELS
    assert np.array_equal(frames.reshape(-1, STEREO_CHANNELS), quantise(sample.pcm, BitDepth.EIGHT) + 128)


def test_a_file_carrying_frames_alone_sounds_at_full_level() -> None:
    body = FORMAT_CHUNK.pack(
        {"encoding": INTEGER_SAMPLES, "channels": 1, "rate": 8000, "byte_rate": 8000, "block_align": 1, "bits": 8}
    )
    plain = wrapped(tagged(FORMAT_TAG, body) + tagged(DATA_TAG, bytes([128, 255, 0, 128])))
    sample = parse_sample(plain)
    assert (sample.name, sample.rate, sample.depth, sample.frames) == ("", 8000, BitDepth.EIGHT, 4)
    assert (sample.volume, sample.gain, sample.panning) == (MAX_VOLUME, MAX_VOLUME, None)
    assert (sample.loop, sample.sustain_loop, sample.vibrato) == (None, None, NO_VIBRATO)


def test_a_placeholder_sample_writes_a_file_holding_no_frames() -> None:
    empty = Sample(name="slot", pcm=np.zeros(0), rate=RATE)
    assert parse_sample(write_sample(empty)) == empty


def test_a_file_stating_no_format_is_refused() -> None:
    with pytest.raises(ValueError, match="fmt "):
        parse_sample(wrapped(tagged(DATA_TAG, b"\x00\x00")))


def test_a_file_stating_a_width_this_library_leaves_alone_is_refused() -> None:
    body = FORMAT_CHUNK.pack(
        {"encoding": INTEGER_SAMPLES, "channels": 1, "rate": 8000, "byte_rate": 24000, "block_align": 3, "bits": 24}
    )
    with pytest.raises(ValueError, match="24-bit"):
        parse_sample(wrapped(tagged(FORMAT_TAG, body) + tagged(DATA_TAG, bytes(6))))


def test_a_file_stating_more_channels_than_stereo_is_refused() -> None:
    body = FORMAT_CHUNK.pack(
        {"encoding": INTEGER_SAMPLES, "channels": 6, "rate": 8000, "byte_rate": 48000, "block_align": 6, "bits": 8}
    )
    with pytest.raises(ValueError, match="6 channels"):
        parse_sample(wrapped(tagged(FORMAT_TAG, body) + tagged(DATA_TAG, bytes(12))))


def test_a_file_stating_amplitudes_of_another_kind_is_refused() -> None:
    body = FORMAT_CHUNK.pack(
        {"encoding": 3, "channels": 1, "rate": 8000, "byte_rate": 32000, "block_align": 4, "bits": 16}
    )
    with pytest.raises(ValueError, match="encoding 3"):
        parse_sample(wrapped(tagged(FORMAT_TAG, body) + tagged(DATA_TAG, bytes(8))))


def test_a_saved_file_reads_back_from_the_path_it_was_written_to(tmp_path: Path) -> None:
    sample = make_sample(loop=Loop(begin=4, end=32))
    path = tmp_path / "lead.wav"
    save_sample(sample, path)
    assert load_sample(path) == sample


def test_a_file_stopping_inside_its_format_chunk_is_refused() -> None:
    with pytest.raises(ValueError, match="format chunk needs"):
        parse_sample(wrapped(tagged(FORMAT_TAG, bytes(8)) + tagged(DATA_TAG, bytes(4))))


def test_a_stored_loop_reaching_no_further_than_it_begins_reads_as_none() -> None:
    # A file may state a loop the frames it holds have long since been cut short of; a reader draws
    # such a loop back inside them, and a range left spanning nothing sounds as no loop at all.
    sample = make_sample(loop=Loop(begin=8, end=48))
    held = unwrapped(write_sample(sample))
    truncated = wrapped(
        tagged(FORMAT_TAG, held[FORMAT_TAG])
        + tagged(DATA_TAG, held[DATA_TAG][:8])
        + tagged(SAMPLER_TAG, held[SAMPLER_TAG])
    )
    assert parse_sample(truncated).loop is None


def test_a_stored_transposition_travels_as_the_rate_it_reaches() -> None:
    # One format tunes the triggering key toward the pitch instead of naming the rate outright; the
    # rate is what that arithmetic arrives at, and it is what an audio file states.
    tuned = Sample(name="lead", pcm=waveform(), rate=RATE, relative_note=12, finetune=64)
    read = parse_sample(write_sample(tuned))
    assert read.rate == RATE
    assert read == tuned.model_copy(update={"relative_note": 0, "finetune": 0})

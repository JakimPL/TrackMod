import pytest

from trackmod.wave.chunks import chunks, formed, required, tagged, unwrapped, wrapped
from trackmod.wave.spec import DATA_TAG, FORMAT_TAG, INFO_FORM, LIST_TAG, NAME_TAG


def test_a_chunk_states_its_tag_then_the_length_that_follows() -> None:
    assert tagged(DATA_TAG, b"abcd") == b"data\x04\x00\x00\x00abcd"


def test_a_chunk_of_odd_length_is_padded_so_the_next_one_starts_even() -> None:
    # The length still names the payload; the pad byte sits past it, which is what keeps every chunk
    # header on an even offset.
    padded = tagged(DATA_TAG, b"abc")
    assert padded == b"data\x03\x00\x00\x00abc\x00"
    assert len(padded) % 2 == 0


def test_a_wrapped_body_reads_back_as_the_chunks_it_holds() -> None:
    body = tagged(FORMAT_TAG, b"01234567") + tagged(DATA_TAG, b"pcm")
    assert unwrapped(wrapped(body)) == {FORMAT_TAG: b"01234567", DATA_TAG: b"pcm"}


def test_a_padded_chunk_is_walked_past_its_pad_byte() -> None:
    body = tagged(DATA_TAG, b"abc") + tagged(FORMAT_TAG, b"xy")
    assert chunks(body) == {DATA_TAG: b"abc", FORMAT_TAG: b"xy"}


def test_a_run_of_chunks_keeps_the_first_of_a_repeated_tag() -> None:
    body = tagged(DATA_TAG, b"first") + tagged(DATA_TAG, b"second")
    assert chunks(body) == {DATA_TAG: b"first"}


def test_a_chunk_stating_more_bytes_than_it_holds_is_read_to_the_end() -> None:
    assert chunks(b"data\xff\x00\x00\x00abc") == {DATA_TAG: b"abc"}


def test_a_list_states_its_form_before_the_chunks_inside_it() -> None:
    payload = INFO_FORM + tagged(NAME_TAG, b"lead\x00")
    assert formed(payload, INFO_FORM) == {NAME_TAG: b"lead\x00"}


def test_a_list_of_another_form_holds_nothing_a_reader_here_wants() -> None:
    assert formed(b"adtl" + tagged(NAME_TAG, b"lead\x00"), INFO_FORM) == {}


def test_bytes_stating_another_container_are_refused() -> None:
    with pytest.raises(ValueError, match="RIFF"):
        unwrapped(b"FORM\x04\x00\x00\x00AIFF")


def test_bytes_stating_another_form_are_refused() -> None:
    with pytest.raises(ValueError, match="WAVE"):
        unwrapped(tagged(b"RIFF", b"AVI "))


def test_bytes_stopping_inside_the_container_are_refused() -> None:
    with pytest.raises(ValueError, match="bytes"):
        unwrapped(b"RIFF\x04")


def test_a_tag_the_file_never_states_is_refused() -> None:
    with pytest.raises(ValueError, match="fmt "):
        required({DATA_TAG: b"pcm"}, FORMAT_TAG)


def test_a_tag_the_file_states_is_the_payload_it_holds() -> None:
    assert required({LIST_TAG: b"INFO"}, LIST_TAG) == b"INFO"

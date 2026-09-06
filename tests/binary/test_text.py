import pytest

from trackmod.binary.text import decode_name, encode_name

LENGTH = 8


@pytest.mark.parametrize("name", ["", "atom", "12345678"])
def test_a_name_round_trips_through_its_fixed_width_field(name: str) -> None:
    assert decode_name(encode_name(name, LENGTH)) == name


def test_a_name_fills_its_field_and_pads_the_rest() -> None:
    assert encode_name("atom", LENGTH) == b"atom" + bytes(4)


def test_an_overlong_name_is_truncated_to_the_field() -> None:
    assert encode_name("far too long a name", LENGTH) == b"far too "


def test_characters_outside_the_tracker_set_become_placeholders() -> None:
    # The tracker set is one byte wide, so a character needing more than that has no byte to be stored as.
    assert decode_name(encode_name("piano\u017c", LENGTH)) == "piano?"


def test_every_byte_a_field_can_hold_survives_being_read_and_written_back() -> None:
    # Trackers of every lineage wrote national characters and box drawing into their name fields, and a
    # module carrying one has to come back out of a rewrite holding the byte it came in with.
    fields = [bytes([byte]) + bytes(LENGTH - 1) for byte in range(1, 256)]
    assert [encode_name(decode_name(field), LENGTH) for field in fields] == fields


def test_a_name_holding_the_high_half_of_the_set_reads_as_the_characters_it_names() -> None:
    assert decode_name(b"ge inte upp nu f\xf6r" + bytes(4)) == "ge inte upp nu för"

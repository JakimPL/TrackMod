import pytest

from trackmod.binary.nibble import decimal_byte, join_nibbles, split_nibbles
from trackmod.spec.width import BYTE_MAX, DECIMAL_BYTE_MAX, NIBBLE_MAX


@pytest.mark.parametrize("value", [0x00, 0x0D, 0xD3, BYTE_MAX])
def test_a_byte_round_trips_through_its_nibbles(value: int) -> None:
    assert join_nibbles(*split_nibbles(value)) == value


def test_the_high_nibble_leads() -> None:
    assert split_nibbles(0xD3) == (0xD, 0x3)
    assert join_nibbles(0xD, 0x3) == 0xD3


@pytest.mark.parametrize("value", [-1, BYTE_MAX + 1])
def test_splitting_something_wider_than_a_byte_raises(value: int) -> None:
    with pytest.raises(ValueError):
        split_nibbles(value)


@pytest.mark.parametrize("nibbles", [(NIBBLE_MAX + 1, 0), (0, -1)])
def test_joining_something_wider_than_a_nibble_raises(nibbles: tuple[int, int]) -> None:
    with pytest.raises(ValueError):
        join_nibbles(*nibbles)


@pytest.mark.parametrize(("value", "stored"), [(0, 0x00), (7, 0x07), (16, 0x16), (DECIMAL_BYTE_MAX, 0x99)])
def test_a_decimal_number_is_stored_a_digit_to_each_nibble(value: int, stored: int) -> None:
    assert decimal_byte(value) == stored


@pytest.mark.parametrize("value", [-1, DECIMAL_BYTE_MAX + 1])
def test_a_number_past_two_decimal_digits_raises(value: int) -> None:
    with pytest.raises(ValueError, match="decimal digits"):
        decimal_byte(value)

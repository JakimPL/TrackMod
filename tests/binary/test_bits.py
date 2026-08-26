import pytest

from trackmod.binary.bits import BitReader


def test_fields_are_read_least_significant_bit_first() -> None:
    # 0b1010_0101 read three bits at a time gives its low bits first.
    reader = BitReader(bytes([0b10100101]))
    assert [reader.take(3), reader.take(3)] == [0b101, 0b100]


def test_a_field_reaches_across_a_byte_boundary() -> None:
    reader = BitReader(bytes([0xFF, 0x01]))
    assert reader.take(9) == 0x1FF


def test_successive_fields_may_each_ask_a_different_width() -> None:
    reader = BitReader(bytes([0b11001101, 0b00000011]))
    assert reader.take(2) == 0b01
    assert reader.take(4) == 0b0011
    assert reader.take(4) == 0b1111


def test_a_zero_width_field_reads_nothing() -> None:
    reader = BitReader(bytes([0xFF]))
    assert reader.take(0) == 0
    assert reader.take(8) == 0xFF


def test_a_stream_shorter_than_the_field_asked_for_is_refused() -> None:
    reader = BitReader(bytes([0xFF]))
    with pytest.raises(ValueError, match="short of"):
        reader.take(9)

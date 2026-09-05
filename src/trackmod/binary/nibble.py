from trackmod.spec.width import BYTE_MAX, DECIMAL_BYTE_MAX, DECIMAL_RADIX, NIBBLE_BITS, NIBBLE_MAX


def split_nibbles(value: int) -> tuple[int, int]:
    """Split a byte into its high and low nibbles.

    Raises:
        ValueError: when ``value`` does not fit in a byte.
    """
    if not 0 <= value <= BYTE_MAX:
        raise ValueError(f"{value} does not fit in a byte")

    return value >> NIBBLE_BITS, value & NIBBLE_MAX


def join_nibbles(high: int, low: int) -> int:
    """Combine two nibbles into a byte.

    Raises:
        ValueError: when either nibble exceeds four bits.
    """
    if not 0 <= high <= NIBBLE_MAX or not 0 <= low <= NIBBLE_MAX:
        raise ValueError(f"nibbles {high}, {low} exceed four bits")

    return (high << NIBBLE_BITS) | low


def decimal_byte(value: int) -> int:
    """The byte a tracker reads back as the decimal number ``value``, a digit to each nibble.

    Amiga ProTracker read one parameter as though its two hexadecimal digits were decimal ones, and the
    trackers that followed it kept the reading, so 16 is stored as ``0x16``.

    Raises:
        ValueError: when ``value`` needs more than two decimal digits.
    """
    if not 0 <= value <= DECIMAL_BYTE_MAX:
        raise ValueError(f"{value} needs more than two decimal digits")

    return join_nibbles(*divmod(value, DECIMAL_RADIX))

from trackmod.spec.text import ENCODING, PADDING, REPLACEMENT


def encode_name(text: str, length: int) -> bytes:
    """Encode ``text`` to exactly ``length`` bytes, null-padded, truncating anything longer.

    Tracker name fields are fixed-width and a player reads the whole width, so a name is padded rather
    than terminated. Characters outside the tracker character set become ``?``.
    """
    raw = text.encode(ENCODING, errors=REPLACEMENT)[:length]
    return raw + PADDING * (length - len(raw))


def decode_name(raw: bytes) -> str:
    """Read a fixed-width name field back, dropping the padding a writer added."""
    return raw.split(PADDING, 1)[0].decode(ENCODING, errors=REPLACEMENT)


def encode_text(text: str) -> bytes:
    """Encode ``text`` as a block of its own length, closed by the terminator a reader stops at.

    A block a header points at with an offset and a length is as long as its content, so the terminator
    is what states where the text ends within the length the header reserves for it. Characters outside
    the tracker character set become ``?``.
    """
    return text.encode(ENCODING, errors=REPLACEMENT) + PADDING


def decode_text(raw: bytes) -> str:
    """Read a terminated text block back, up to where its terminator closes it."""
    return raw.split(PADDING, 1)[0].decode(ENCODING, errors=REPLACEMENT)

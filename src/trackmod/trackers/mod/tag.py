from trackmod.trackers.mod.dialect import (
    DEFAULT_DIALECT,
    DIALECTS,
    WIDE_DIALECT,
    Dialect,
    channel_tag,
)
from trackmod.trackers.mod.spec.dialects import SPLIT_TAGS
from trackmod.trackers.mod.spec.identity import TAG_BYTES, TAG_OFFSET
from trackmod.trackers.mod.spec.ranges import CANONICAL_CHANNELS, TAGGED_MAX_PATTERNS


def stated_tag(data: bytes) -> bytes:
    """The four tag bytes a module carries after its order table.

    Raises:
        ValueError: when the data stops before the header does.
    """
    end = TAG_OFFSET + TAG_BYTES
    if len(data) < end:
        raise ValueError(f"a module header is {end} bytes, and the data holds {len(data)}")

    return data[TAG_OFFSET:end]


def detected(data: bytes) -> Dialect:
    """The dialect a module's tag names, which settles how many channels its patterns are wide.

    Raises:
        ValueError: when the tag names a layout this format reads no patterns from, or names none of
            the dialects at all — which is what the 15-sample layout written before any tag existed
            reads as.
    """
    tag = stated_tag(data)
    dialect = DIALECTS.get(tag)
    if dialect is not None:
        return dialect

    split = SPLIT_TAGS.get(tag)
    if split is not None:
        raise ValueError(f"the tag {tag!r} names a layout that {split}")

    raise ValueError(f"the tag {tag!r} names none of the dialects this format reads")


def chosen(*, channels: int, patterns: int) -> Dialect:
    """The dialect a song is written under: the one whose tag states the width its patterns hold.

    Four channels is what Amiga ProTracker itself wrote, and it has two tags: the plain one, and the one
    a tracker writes once a song holds more patterns than the plain tag was read with. Every other width
    is spelled by the multichannel families, a digit to a character.

    Raises:
        ValueError: when no dialect states that many channels.
    """
    if channels == CANONICAL_CHANNELS:
        return DEFAULT_DIALECT if patterns <= TAGGED_MAX_PATTERNS else WIDE_DIALECT

    dialect = DIALECTS.get(channel_tag(channels))
    if dialect is None:
        raise ValueError(f"no dialect states {channels} channels")

    return dialect

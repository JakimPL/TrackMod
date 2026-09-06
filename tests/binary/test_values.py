from collections.abc import Callable

import pytest

from trackmod.binary.records.values import (
    ArrayValue,
    RecordValues,
    read_bytes,
    read_int,
    read_rows,
)

Reader = Callable[[RecordValues, str], int | bytes | ArrayValue]

VALUES: RecordValues = {"count": 4, "name": b"lead", "table": ((1, 2), (3, 4))}


def test_each_reader_answers_the_field_it_is_asked_for() -> None:
    assert read_int(VALUES, "count") == 4
    assert read_bytes(VALUES, "name") == b"lead"
    assert read_rows(VALUES, "table") == ((1, 2), (3, 4))


@pytest.mark.parametrize(
    ("reader", "name", "expected"),
    [
        (read_int, "name", "expected an integer"),
        (read_int, "table", "expected an integer"),
        (read_bytes, "count", "expected a byte block"),
        (read_bytes, "table", "expected a byte block"),
        (read_rows, "count", "expected a run of elements"),
        (read_rows, "name", "expected a run of elements"),
    ],
)
def test_a_field_read_as_the_wrong_kind_names_what_it_holds(reader: Reader, name: str, expected: str) -> None:
    # A record states the shape of every field it defines, so reading one as another kind is a mistake
    # in the reader rather than a value a file got wrong -- which is why it is a TypeError.
    with pytest.raises(TypeError, match=expected):
        reader(VALUES, name)

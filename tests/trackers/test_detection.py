from collections.abc import Callable
from typing import Final

import pytest

from trackmod.trackers.it.detection import instrument_written_here as it_instrument
from trackmod.trackers.it.detection import written_here as it_module
from trackmod.trackers.mod.detection import written_here as mod_module
from trackmod.trackers.s3m.detection import written_here as s3m_module
from trackmod.trackers.st.detection import written_here as st_module
from trackmod.trackers.xm.detection import instrument_written_here as xm_instrument
from trackmod.trackers.xm.detection import written_here as xm_module

Predicate = Callable[[bytes], bool]

PREDICATES: Final[tuple[tuple[str, Predicate], ...]] = (
    ("it", it_module),
    ("xm", xm_module),
    ("s3m", s3m_module),
    ("mod", mod_module),
    ("st", st_module),
    ("iti", it_instrument),
    ("xi", xm_instrument),
)

NOTHING: Final = (b"", b"\x00", b"not a module at all")


@pytest.mark.parametrize(("name", "states"), PREDICATES, ids=[name for name, _ in PREDICATES])
def test_a_format_reads_itself_into_none_of_the_bytes_that_hold_nothing(name: str, states: Predicate) -> None:
    # A predicate is asked of whatever a caller holds, so it answers for data far shorter than a header
    # rather than reaching past the end of it.
    assert [states(data) for data in NOTHING] == [False, False, False], name

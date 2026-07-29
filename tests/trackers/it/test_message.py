import pytest

from trackmod.core.songs.song import Song
from trackmod.limits.capability import Capability
from trackmod.limits.compliance import Compliance
from trackmod.limits.severity import Severity
from trackmod.spec.width import WORD_MAX
from trackmod.trackers.it.message import MessageBlock, message_data
from trackmod.trackers.it.module import ITModule
from trackmod.trackers.it.settings import ITSettings
from trackmod.trackers.it.spec.flags import SpecialFlag
from trackmod.trackers.it.spec.ranges import CANONICAL_MAX_MESSAGE_BYTES

MESSAGE = "written by trackmod\rline two"
TERMINATOR_BYTES = 1


def module(song: Song, message: str, *, compliance: Compliance = Compliance.EXTENDED) -> ITModule:
    return ITModule.from_song(song, compliance=compliance, settings=ITSettings(message=message))


def test_a_module_attaching_no_message_reads_back_none(song: Song) -> None:
    recovered = ITModule.parse(module(song, "").to_bytes())
    assert recovered.settings.message == ""


def test_a_message_survives_a_round_trip(song: Song) -> None:
    recovered = ITModule.parse(module(song, MESSAGE).to_bytes())
    assert recovered.settings.message == MESSAGE
    assert recovered.song == ITModule.parse(module(song, "").to_bytes()).song


def test_a_message_is_stored_where_the_header_points_at_it(song: Song) -> None:
    data = module(song, MESSAGE).to_bytes()
    block = MessageBlock.of(MESSAGE, start=len(data) - len(message_data(MESSAGE)))
    assert data[block.offset : block.offset + block.length] == message_data(MESSAGE)
    assert block.special is SpecialFlag.MESSAGE


def test_a_message_grows_the_file_by_the_block_it_takes(song: Song) -> None:
    growth = len(module(song, MESSAGE).to_bytes()) - len(module(song, "").to_bytes())
    assert growth == len(MESSAGE) + TERMINATOR_BYTES


def test_the_size_model_agrees_with_a_file_carrying_a_message(song: Song) -> None:
    carrying = module(song, MESSAGE)
    assert carrying.size().total == len(carrying.to_bytes())


@pytest.mark.parametrize(
    ("length", "compliance", "severity"),
    [
        (CANONICAL_MAX_MESSAGE_BYTES, Compliance.CANONICAL, Severity.COMPLIANCE),
        (WORD_MAX, Compliance.EXTENDED, Severity.STRUCTURAL),
    ],
    ids=["canonical", "structural"],
)
def test_a_message_past_what_the_container_holds_is_reported(
    song: Song,
    length: int,
    compliance: Compliance,
    severity: Severity,
) -> None:
    (violation,) = module(song, "m" * length, compliance=compliance).violations()
    assert violation.capability is Capability.MESSAGE_BYTES
    assert violation.severity is severity
    assert violation.value == length + TERMINATOR_BYTES


def test_a_message_the_tracker_reads_breaks_no_bound(song: Song) -> None:
    longest = "m" * (CANONICAL_MAX_MESSAGE_BYTES - TERMINATOR_BYTES)
    assert module(song, longest, compliance=Compliance.CANONICAL).violations() == ()

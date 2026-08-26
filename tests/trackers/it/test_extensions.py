import pytest

from trackmod.core.songs.song import Song
from trackmod.limits.compliance import Compliance
from trackmod.trackers.it.extensions import Extensions, block_names, named_block
from trackmod.trackers.it.module import ITModule
from trackmod.trackers.it.settings import ITSettings
from trackmod.trackers.it.spec.extensions import (
    CHANNEL_NAME_BYTES,
    CHANNEL_NAMES_MAGIC,
    PATTERN_NAME_BYTES,
    PATTERN_NAMES_MAGIC,
)
from trackmod.trackers.it.spec.flags import SpecialFlag

CHANNELS = ("Kick", "Snare", "")
HISTORY = bytes([2, 0]) + bytes(16)
APPENDED = b"STPM" + bytes(20)


def carried(**stated: object) -> ITSettings:
    """Settings carrying one set of extensions, which is what a written module states them from."""
    return ITSettings(extensions=Extensions(**stated))


@pytest.mark.parametrize(
    ("magic", "width", "names"),
    [
        (CHANNEL_NAMES_MAGIC, CHANNEL_NAME_BYTES, CHANNELS),
        (PATTERN_NAMES_MAGIC, PATTERN_NAME_BYTES, ("intro", "verse")),
    ],
    ids=("channels", "patterns"),
)
def test_a_block_of_names_reads_back_the_names_it_was_written_from(
    magic: bytes, width: int, names: tuple[str, ...]
) -> None:
    assert block_names(named_block(magic, names, width=width), magic, width=width) == names


def test_a_block_that_states_no_names_occupies_nothing() -> None:
    assert named_block(CHANNEL_NAMES_MAGIC, (), width=CHANNEL_NAME_BYTES) == b""


def test_a_region_states_each_block_it_holds_whatever_order_they_sit_in() -> None:
    region = named_block(PATTERN_NAMES_MAGIC, ("intro",), width=PATTERN_NAME_BYTES) + named_block(
        CHANNEL_NAMES_MAGIC, CHANNELS, width=CHANNEL_NAME_BYTES
    )
    assert block_names(region, CHANNEL_NAMES_MAGIC, width=CHANNEL_NAME_BYTES) == CHANNELS
    assert block_names(region, PATTERN_NAMES_MAGIC, width=PATTERN_NAME_BYTES) == ("intro",)


def test_a_block_this_library_has_no_reading_for_is_stepped_over() -> None:
    # A later writer states blocks of its own, and the ones beside them are still reachable.
    region = named_block(b"ZZZZ", ("opaque",), width=8) + named_block(
        CHANNEL_NAMES_MAGIC, CHANNELS, width=CHANNEL_NAME_BYTES
    )
    assert block_names(region, CHANNEL_NAMES_MAGIC, width=CHANNEL_NAME_BYTES) == CHANNELS


def test_a_block_reaching_past_the_data_behind_it_is_refused() -> None:
    truncated = named_block(CHANNEL_NAMES_MAGIC, CHANNELS, width=CHANNEL_NAME_BYTES)[:-10]
    with pytest.raises(ValueError, match="states"):
        block_names(truncated, CHANNEL_NAMES_MAGIC, width=CHANNEL_NAME_BYTES)


def test_an_editing_history_asks_the_header_for_the_switch_that_finds_it() -> None:
    # Nothing points at the history, so the switch is the whole of how a reader knows it is there.
    assert Extensions(history=HISTORY).special is SpecialFlag.HISTORY
    assert Extensions().special == SpecialFlag(0)


def test_a_module_carries_every_block_it_arrived_with(song: Song) -> None:
    settings = carried(channel_names=CHANNELS, pattern_names=("intro",), history=HISTORY, appended=APPENDED)
    written = ITModule.from_song(song, compliance=Compliance.EXTENDED, settings=settings).to_bytes()
    recovered = ITModule.parse(written)
    assert recovered.settings.extensions == settings.extensions
    # The blocks move every offset the header states, so the records behind them must still be found.
    assert recovered.song.patterns == song.patterns
    assert recovered.song.instruments == song.instruments
    assert [sample.name for sample in recovered.song.samples] == [sample.name for sample in song.samples]


def test_the_blocks_move_every_record_the_header_points_at(song: Song) -> None:
    # They sit between the offset tables and the records, so a file carrying them is longer by their size.
    plain = ITModule.from_song(song, compliance=Compliance.EXTENDED)
    carrying = ITModule.from_song(
        song, compliance=Compliance.EXTENDED, settings=carried(channel_names=CHANNELS, appended=APPENDED)
    )
    grew = len(carrying.to_bytes()) - len(plain.to_bytes())
    assert grew == carrying.settings.extensions.named_bytes + len(APPENDED)


def test_the_size_model_agrees_with_the_writer_over_the_blocks(song: Song) -> None:
    settings = carried(channel_names=CHANNELS, history=HISTORY, appended=APPENDED)
    module = ITModule.from_song(song, compliance=Compliance.EXTENDED, settings=settings)
    assert module.size().total == len(module.to_bytes())

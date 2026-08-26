import pytest

from trackmod.binary.volume import VolumeColumn, VolumeSpan
from trackmod.core.volumes.command import VolumeCommand, VolumeEffect
from trackmod.limits.bound import Bound
from trackmod.trackers.it.spec.volume import VOLUME_COLUMN as IMPULSE_TRACKER
from trackmod.trackers.xm.spec.volume import VOLUME_COLUMN as FAST_TRACKER

COLUMNS = (IMPULSE_TRACKER, FAST_TRACKER)


@pytest.mark.parametrize("column", COLUMNS, ids=("it", "xm"))
def test_every_run_the_column_states_reads_back_as_itself(column: VolumeColumn) -> None:
    for span in column.spans:
        for amount in (span.amounts.minimum, span.amounts.maximum):
            command = VolumeCommand(effect=span.effect, amount=amount)
            assert column.stated(column.stored(command)) == command


@pytest.mark.parametrize("column", COLUMNS, ids=("it", "xm"))
def test_every_level_the_column_holds_reads_back_as_itself(column: VolumeColumn) -> None:
    for level in (column.levels.minimum, column.levels.maximum):
        assert column.stated(column.stored(level)) == level


@pytest.mark.parametrize("column", COLUMNS, ids=("it", "xm"))
def test_the_runs_a_column_states_stay_apart(column: VolumeColumn) -> None:
    # Two runs sharing a byte would read one effect as another, so every stored byte names one run.
    stored = [
        column.stored(VolumeCommand(effect=span.effect, amount=amount))
        for span in column.spans
        for amount in range(span.amounts.minimum, span.amounts.maximum + 1)
    ]
    assert len(set(stored)) == len(stored)
    assert all(byte not in range(column.level_base, column.level_base + column.levels.room) for byte in stored)


@pytest.mark.parametrize("column", COLUMNS, ids=("it", "xm"))
def test_a_column_answers_only_for_the_effects_it_names(column: VolumeColumn) -> None:
    named = {span.effect for span in column.spans}
    assert named
    assert all(column.span(effect) is not None for effect in named)
    assert all(column.span(effect) is None for effect in set(VolumeEffect) - named)


def test_an_effect_a_column_leaves_unnamed_states_why() -> None:
    unnamed = VolumeCommand(effect=VolumeEffect.VIBRATO_SPEED, amount=0)
    assert IMPULSE_TRACKER.stored(unnamed) is None
    assert "no run for" in IMPULSE_TRACKER.refusal(unnamed)


def test_an_amount_past_its_run_states_the_amounts_the_run_holds() -> None:
    span = FAST_TRACKER.span(VolumeEffect.PORTAMENTO)
    assert span is not None
    past = VolumeCommand(effect=span.effect, amount=span.amounts.maximum + 1)
    assert FAST_TRACKER.stored(past) is None
    assert str(span.amounts) in FAST_TRACKER.refusal(past)


def test_a_level_past_the_column_states_the_levels_it_holds() -> None:
    column = VolumeColumn(
        level_base=0,
        levels=Bound(minimum=0, maximum=8),
        spans=(VolumeSpan(effect=VolumeEffect.PANNING, base=16, amounts=Bound(minimum=0, maximum=3)),),
        absent=None,
    )
    assert column.stored(9) is None
    assert "0..8" in column.refusal(9)


def test_the_byte_a_format_writes_for_no_volume_states_no_volume() -> None:
    assert FAST_TRACKER.states_volume(FAST_TRACKER.level_base)
    assert not FAST_TRACKER.states_volume(0x00)
    assert FAST_TRACKER.stated(0x00) is None


def test_the_two_columns_share_the_vocabulary_the_documents_state() -> None:
    # docs/volume.md counts these, so a run added to either column brings the count with it.
    impulse = {span.effect for span in IMPULSE_TRACKER.spans}
    fast = {span.effect for span in FAST_TRACKER.spans}
    assert (len(impulse), len(fast), len(impulse & fast)) == (9, 10, 7)
    assert impulse | fast == set(VolumeEffect)
    assert impulse - fast == {VolumeEffect.PITCH_SLIDE_UP, VolumeEffect.PITCH_SLIDE_DOWN}


def test_an_amount_both_columns_count_carries_a_command_between_them() -> None:
    portable = min(span.amounts.maximum for column in COLUMNS for span in column.spans)
    for effect in {span.effect for span in IMPULSE_TRACKER.spans} & {span.effect for span in FAST_TRACKER.spans}:
        command = VolumeCommand(effect=effect, amount=portable)
        assert IMPULSE_TRACKER.stored(command) is not None
        assert FAST_TRACKER.stored(command) is not None

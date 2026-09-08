from enum import IntEnum

from trackmod.core.instruments.instrument import Instrument
from trackmod.core.repairs.report import Repairs


def routed_within(instrument: Instrument, *, samples: int, subject: str, repairs: Repairs) -> Instrument:
    """An instrument whose keys reach only the samples the song carries.

    A keymap states a sample number per key, and files carry numbers past the samples they store -- most
    often where an instrument outlived the waveform it was written against. Those keys are left silent,
    which is what a tracker plays for a key routed nowhere.
    """
    keymap = tuple(
        (assignment if assignment is not None and assignment.sample < samples else None)
        for assignment in instrument.keymap
    )
    silenced = sum(1 for before, after in zip(instrument.keymap, keymap) if before is not after)
    if silenced == 0:
        return instrument

    repairs.made(
        f"{silenced} keys routed past the {samples} samples stored are left silent",
        subject=subject,
    )
    return instrument.model_copy(update={"keymap": keymap})


def stated_behavior[Behavior: IntEnum](
    value: int,
    *,
    among: type[Behavior],
    default: Behavior,
    name: str,
    subject: str,
    repairs: Repairs,
) -> Behavior:
    """The behavior a stored byte names, or the one a fresh instrument carries where it names none.

    Files carry bytes past the behaviors a format numbers, most often where a field was left as it was
    found in memory, so such a byte is read as the behavior a tracker starts an instrument with.
    """
    numbered = {int(member): member for member in among}
    behavior = numbered.get(value)
    if behavior is not None:
        return behavior

    repairs.made(f"{name} {value} read as {default.name}", subject=subject)
    return default

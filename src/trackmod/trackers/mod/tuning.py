from typing import Final

from trackmod.trackers.mod.spec.periods import FINETUNE_PERIODS, FINETUNE_RATES

FINETUNES: Final = tuple(range(len(FINETUNE_PERIODS)))


def finetune_rate(finetune: int) -> int:
    """The rate a sample stored at one finetune step plays its own key at.

    Amiga ProTracker trims a sample by scaling every period it sounds, in the ratio between the tabulated
    key its finetune row opens on and the one the untrimmed row opens on. Sixteen rows are tabulated, so
    a stored sample reaches sixteen rates and the step between them is an eighth of a semitone.
    """
    return FINETUNE_RATES[finetune]


def finetune_for(rate: int) -> int:
    """The finetune step whose rate comes closest to ``rate`` in pitch.

    The lattice is the whole reach this format has: a sample recorded outside it is graded against
    :data:`~trackmod.limits.capability.Capability.SAMPLE_RATE`, which tells a caller to resample it to
    one the sixteen rows hold before writing.
    """
    return min(FINETUNES, key=lambda finetune: max(rate / FINETUNE_RATES[finetune], FINETUNE_RATES[finetune] / rate))

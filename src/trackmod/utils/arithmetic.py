from math import isqrt


def divisors(number: int) -> list[int]:
    """Every divisor of ``number``, in ascending order.

    Each divisor below the square root pairs with one above it, so walking up to the root finds both
    halves at once and the run is complete once the two are joined.
    """
    below: list[int] = []
    above: list[int] = []
    for candidate in range(1, isqrt(number) + 1):
        if number % candidate:
            continue

        below.append(candidate)
        if candidate != number // candidate:
            above.append(number // candidate)

    return below + above[::-1]


def neighbor_divisors(candidate: int, dividend: int) -> tuple[int | None, int | None]:
    """The divisors of ``dividend`` that ``candidate`` falls between, as the pair below it and above it.

    A candidate that divides the dividend is its own neighbour on both sides. Each side is answered
    separately, and a side with no divisor on it is answered as absent.

    Raises:
        ValueError: when ``candidate`` falls outside ``1..dividend``.
    """
    if candidate < 1 or candidate > dividend:
        raise ValueError(f"candidate {candidate} must be in 1..{dividend}")

    if not dividend % candidate:
        return candidate, candidate

    below: int | None = None
    above: int | None = None
    for divisor in divisors(dividend):
        if divisor > candidate:
            above = divisor
            break

        below = divisor

    return below, above

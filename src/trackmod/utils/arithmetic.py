from math import isqrt


def divisors(n: int) -> list[int]:
    small: list[int] = []
    large: list[int] = []

    for d in range(1, isqrt(n) + 1):
        if n % d == 0:
            small.append(d)
            if d != n // d:
                large.append(n // d)

    return small + large[::-1]


def neighbor_divisors(
    candidate: int,
    dividend: int,
) -> tuple[int | None, int | None]:
    if candidate < 1 or candidate > dividend:
        raise ValueError("candidate must be in [1, dividend]")

    if not dividend % candidate:
        return candidate, candidate

    candidates = divisors(dividend)
    previous_candidate: int | None = None
    low: int | None = None
    high: int | None = None
    for cand in candidates:
        difference = cand - candidate
        if difference >= 0:
            low = previous_candidate
            high = cand
            break

        previous_candidate = cand

    return low, high

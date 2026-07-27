from collections.abc import Sequence


def offsets(blobs: Sequence[bytes], start: int) -> list[int]:
    """Where each blob lands when they are laid end to end from ``start``."""
    positions = []
    position = start
    for blob in blobs:
        positions.append(position)
        position += len(blob)

    return positions

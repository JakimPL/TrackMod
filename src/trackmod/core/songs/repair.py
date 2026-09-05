from trackmod.core.repairs.report import Repairs
from trackmod.core.songs.order import OrderList


def repaired_order(order: OrderList, *, patterns: int, subject: str, repairs: Repairs) -> OrderList:
    """An order list holding the positions that name a pattern the file carries.

    Trackers leave positions in the table naming patterns a file never stored, and players step over
    them, so they are dropped here. The restart position follows the entries that remain.
    """
    entries = tuple(entry for entry in order.entries if entry < patterns)
    if len(entries) == len(order.entries):
        return order

    dropped = len(order.entries) - len(entries)
    repairs.made(f"{dropped} order positions naming no stored pattern dropped", subject=subject)
    return OrderList(entries=entries, restart=min(order.restart, max(len(entries) - 1, 0)))

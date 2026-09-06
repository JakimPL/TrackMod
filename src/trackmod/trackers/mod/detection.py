from trackmod.trackers.mod.tag import tagged


def written_here(data: bytes) -> bool:
    """Whether the bytes hold a module of this format, which its tag is the whole of what states.

    Amiga ProTracker wrote no magic in front of a file and no version anywhere, so the four bytes after
    the order table are what a file of it says about itself, and carrying one a reader knows is what
    tells it from the layout written before any tag existed.
    """
    return tagged(data)

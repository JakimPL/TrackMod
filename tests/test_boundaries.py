import ast
from pathlib import Path
from typing import Final

SOURCE: Final = Path("src/trackmod")

TRACKERS: Final = SOURCE / "trackers"

PACKAGES: Final = frozenset(path.name for path in TRACKERS.iterdir() if (path / "__init__.py").exists())
FORMATS: Final = frozenset(name for name in PACKAGES if (TRACKERS / name / "module.py").exists())
LINEAGES: Final = PACKAGES - FORMATS

LAYERS: Final = ("spec", "utils", "schema", "limits", "core", "binary", "module", "trackers")


def modules() -> tuple[Path, ...]:
    """Every source file the library holds, which is what the boundaries are stated over."""
    return tuple(sorted(path for path in SOURCE.rglob("*.py") if path.stat().st_size))


def imported(path: Path) -> tuple[str, ...]:
    """Every ``trackmod`` module one file imports, as the dotted paths its statements name."""
    names: list[str] = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("trackmod"):
            names.append(node.module)
        elif isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names if alias.name.startswith("trackmod"))

    return tuple(names)


def holder(path: Path) -> str:
    """Which format or lineage package a file belongs to, empty where it sits below them."""
    parts = path.relative_to(SOURCE).parts
    return parts[1] if parts[0] == "trackers" and len(parts) > 1 else ""


def reached(module: str) -> str:
    """Which format or lineage package a dotted path names, empty where it names none."""
    parts = module.split(".")
    return parts[2] if len(parts) > 2 and parts[1] == "trackers" else ""


def crossings(owners: frozenset[str], forbidden: frozenset[str]) -> tuple[str, ...]:
    """Every import a package of ``owners`` makes into a package of ``forbidden`` other than its own."""
    return tuple(
        f"{path}: {module}"
        for path in modules()
        if holder(path) in owners
        for module in imported(path)
        if reached(module) in forbidden - {holder(path)}
    )


def test_every_package_under_trackers_is_a_format_or_a_lineage() -> None:
    # A format package binds a module, so the file that binds it is what tells the two apart and no
    # package can be added to either side by accident.
    assert FORMATS == {"it", "xm", "mod", "s3m", "st"}
    assert LINEAGES == {"amiga"}


def test_a_format_package_reads_no_other_format_package() -> None:
    # What one format decides is its own. Two formats sharing a decision share it through the lineage
    # that settled it, so a sibling is never the owner and never the import.
    assert crossings(FORMATS, FORMATS) == ()


def test_a_lineage_package_reads_no_format_package() -> None:
    # A lineage owns what the formats inherited from it, so it states its decisions without knowing
    # which of them reads them, and every format reading it stays free to differ elsewhere.
    assert crossings(LINEAGES, FORMATS | LINEAGES) == ()


def test_a_layer_reads_only_the_layers_beneath_it() -> None:
    # The order is the one `docs/overview.md` states, and a package reads its own layer and the ones
    # below it, so knowing where a name lives is knowing what may reach it.
    inverted = tuple(
        f"{path}: {module}"
        for path in modules()
        for module in imported(path)
        if (parts := module.split("."))[1:2] and parts[1] in LAYERS
        if LAYERS.index(parts[1]) > LAYERS.index(path.relative_to(SOURCE).parts[0])
    )
    assert inverted == ()

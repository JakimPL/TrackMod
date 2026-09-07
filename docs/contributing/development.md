# Development

## The tools

```
make format     # isort + black
make lint       # mypy --strict + pylint
make test       # pytest
make coverage   # pytest with a coverage report
```

Dependencies are managed with `uv`, and the package is built with `hatchling`. Every command above runs
through `uv run`, so a checkout needs no environment of its own.

`pre-commit` runs the same checks on the files a commit touches: trailing whitespace, `isort`, `black`,
`mypy` and `pylint`, with the full test suite as a pre-push hook. Install it once with
`uv run pre-commit install`, and run it over everything with `uv run pre-commit run --all-files`.

## Typing

`mypy` runs in `--strict` mode over `src/trackmod`, with the pydantic plugin and `init_typed`. Every
signature states its input and return types, including `None`, and generic types are filled in:
`dict[str, int]` rather than a bare `dict`. A cast or an `ignore` is for an untyped or mistyped
third-party boundary, and nothing else.

## Linting

`pylint` runs over `src/trackmod` with `fail-under=9.9` and the `pylint_pydantic` plugin. Docstring
requirements for modules, classes and functions are off, because the library carries no module docstrings
and states class and function intent in its own words rather than to a checker.

Duplicate-code reporting is off, because the five format packages repeat one shape on purpose and every
remaining report is that shape. What two formats share for a reason belongs to their lineage, and
`tests/test_boundaries.py` is what holds the line instead.

Both `black` and `isort` run at a line length of 120, `isort` under the `black` profile with `trackmod`
as the first-party package.

## Tests

The test tree mirrors the source tree: `tests/binary`, `tests/core`, `tests/limits`, `tests/module`,
`tests/wave` and `tests/trackers/<format>`, with the shared fixtures — a song, its voices, an envelope,
the waveform helpers — in `tests/conftest.py`.

Three suites sit at the top level and cross those boundaries:

| Suite | What it holds |
|---|---|
| `tests/test_formats.py` | One property stated once for every format, through a `Binding` per format |
| `tests/test_package.py` | What the package root offers, and the loops the guide shows, end to end |
| `tests/test_boundaries.py` | The import graph: the layer order, and what a format or lineage package may read |

`filterwarnings = ["error"]` means a stray `RepairWarning` fails a test rather than printing, so a parser
that starts repairing something new is caught where it happens. Coverage gates at 90 percent.

## Style

- Keep code modular around clear ownership boundaries, and prefer subpackages to large modules.
- A function with several meaningful steps splits into helpers with one responsibility each.
- Names are written out: `note`, not `n`.
- Default values are for what is rarely changed, and each one is a `Final` constant at module level.
- Let failures crash unless the code can recover meaningfully. Bare `except` and `except Exception` are
  out; an error-handling block covers only what can fail.
- The library carries no module docstrings and no code comments. Class and function docstrings state
  intent; the domain and format narrative lives in these documents. A comment is for a tensor shape, a
  third-party quirk, or an invariant the code cannot show on its own.

## Commit messages

One line, in the form *Did: what* — `Added: the fifteen-sample Soundtracker layout`, `Fixed: the
truncations that read as silence`, `Rewrote: the README in plain English`.

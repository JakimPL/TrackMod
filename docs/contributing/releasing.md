# Releasing

A release is a tag. Pushing `vX.Y.Z` runs [`release.yml`](../../.github/workflows/release.yml), which:

1. checks that the tag names the version in `pyproject.toml`, and that `CHANGELOG.md` holds a dated
   section for it,
2. builds the sdist and the wheel once, and checks both with `twine check --strict`,
3. runs the test suite against the built wheel,
4. publishes both files to PyPI through Trusted Publishing, once the maintainer approves the `pypi`
   environment, and PyPI stores a signed attestation beside each file,
5. creates the GitHub release, with the changelog section as its notes and both files attached.

The first two checks run before anything is published, so a tag with the wrong version or an undated
changelog stops the run while PyPI still holds only the earlier releases.

## One-time setup

### PyPI and TestPyPI

On PyPI, under *Account settings → Publishing*, add a pending publisher:

| Field | Value |
|---|---|
| PyPI project name | `trackmod` |
| Owner | `JakimPL` |
| Repository name | `TrackMod` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

Add the same publisher on [TestPyPI](https://test.pypi.org/), with the environment `testpypi`. The first
upload claims the name, so release soon after adding the pending publisher.

### GitHub

Under *Settings → Environments*:

- `pypi`: the maintainer as a required reviewer, and deployments limited to tags matching `v*`.
- `testpypi`: deployments limited to the `main` branch.

Under *Settings → Rules → Rulesets*, add a tag ruleset targeting `v*` that restricts updates and
deletions, so every published version keeps pointing at the commit it was built from.

## Rehearsing on TestPyPI

Once `release.yml` is on `main`, open *Actions → Release → Run workflow* and run it on `main`. The run
numbers the package as a development release, `X.Y.Z.dev<run number>`, because TestPyPI accepts each
version once, and publishes it to TestPyPI. Check the page at <https://test.pypi.org/p/trackmod>, then
install that version:

```bash
uv run --no-project --index https://test.pypi.org/simple/ --index-strategy unsafe-best-match \
    --with "trackmod==X.Y.Z.dev<run number>" python -c "import trackmod; print(trackmod.__version__)"
```

## Each release

1. Set the version with `uv version X.Y.Z`. It updates both `pyproject.toml` and `uv.lock`; commit both.
2. Date the changelog section: `## vX.Y.Z [YYYY-MM-DD]`.
3. Push `main` and wait for CI to pass on that commit.
4. Tag the commit and push the tag:

   ```bash
   git tag -a vX.Y.Z -m "TrackMod vX.Y.Z"
   git push origin vX.Y.Z
   ```

5. Approve the `pypi` deployment in the run.
6. Install the release from PyPI:

   ```bash
   uv run --no-project --with "trackmod==X.Y.Z" python -c "import trackmod; print(trackmod.__version__)"
   ```

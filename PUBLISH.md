# Publishing stemsplit-python

Package: `stemsplit-python` on [PyPI](https://pypi.org/project/stemsplit-python/)
GitHub: https://github.com/StemSplit/stemsplit-python

## Publish workflow

Publishing is fully automated via GitHub Actions (`release.yml`). Never publish manually from a local machine.

### Steps to release a new version

1. **Bump the version** in `pyproject.toml`:
   ```toml
   version = "0.2.0"
   ```

2. **Update `CHANGELOG.md`** with the new release notes.

3. **Commit and push** to `main`:
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore: bump version to 0.2.0"
   git push origin main
   ```

4. **Create and push a tag** — this triggers the CI release:
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

5. CI will:
   - Build sdist + wheel using `uv build`
   - Publish to PyPI using `uv publish` with the `UV_PUBLISH_TOKEN` secret
   - Upload distribution artifacts to the GitHub release

### Required secrets (set in GitHub repo settings)

| Secret | Description |
|--------|-------------|
| `UV_PUBLISH_TOKEN` | PyPI API token for the `stemsplit-python` project |

### Local dev / testing

```bash
cd scripts/packages/stemsplit-python
uv sync
uv run pytest
uv run ruff check src/
uv run mypy src/
```

Build locally (do NOT push to PyPI):
```bash
uv build
# inspect dist/ but do not run uv publish
```

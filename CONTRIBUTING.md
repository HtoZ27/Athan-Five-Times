# Contributing to Athan Five Times

## Development setup

```bash
pip install -r requirements-lock.txt
./run.sh
```

## Quality gates (must pass before any pull request)

```bash
python3 -m pytest tests/
ruff check backend/ tests/ && ruff format --check backend/ tests/
python3 scripts/smoke-qml.py
python3 scripts/e2e-features.py
bash scripts/sync-appdir.sh && bash scripts/sync-appdir.sh --check-only
```

## Conventions

- Python code is formatted with `ruff format`; QML follows the existing file style.
- Settings stay immutable-style: build new dicts, never mutate in place.
- User-visible strings go through `tr()` / `translate()` — no hardcoded Arabic
  in new QML except as translation keys with `ar.json` entries.
- No emoji in user-facing labels; use the PNG icon sets under `assets/`.
- `AppDir/usr/` is derived — never edit it directly, regenerate with
  `scripts/sync-appdir.sh`.
- Do not commit binaries (`*.AppImage`, `*.deb`, `*.rpm`, `*.pkg.tar.*`);
  release artifacts are uploaded to GitHub Releases.

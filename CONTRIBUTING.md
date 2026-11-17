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

## Translation review

Native-speaker review is tracked in
[`docs/dev/HISN-REVIEW-QUEUE.md`](docs/dev/HISN-REVIEW-QUEUE.md). The queue lists
every string that was composed or adapted instead of copied from a published
translation, with the Arabic, the current text, the source and the reason.

- Review only what you are qualified to judge; partial reviews are welcome.
- To sign off, remove the language from `translation_meta.needs_review[item]`
  in `assets/adhkar/{morning,evening}.json` and from `NEEDS_REVIEW` in
  `tests/test_adhkar_repo.py`.
- Keep `pa` in Gurmukhi script, and do not change other locales in the same
  pull request.
- Run `python3 -m pytest tests/test_adhkar_repo.py -q` before opening the pull
  request.

If you would rather not use Git, comment on the pinned review issue instead.

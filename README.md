# أذان الأوقات الخمس (Athan Five Times)

[![CI](https://github.com/HtoZ27/Athan-Five-Times/actions/workflows/ci.yml/badge.svg)](https://github.com/HtoZ27/Athan-Five-Times/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/HtoZ27/Athan-Five-Times?include_prereleases)](https://github.com/HtoZ27/Athan-Five-Times/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Qt 6 QML](https://img.shields.io/badge/Qt-6_QML-green?logo=qt&logoColor=white)](https://www.qt.io/)

> **Beta (0.3.15b)** — This is a beta release: not yet bug-free, not yet
> tested on all Linux environments, and translations are still unreviewed.
> Bug reports are welcome via GitHub Issues.

A Linux desktop prayer-times application with azan audio, structured adhkar, do-not-disturb, and multi-language support. Built with Python + PySide6 (Qt6/QML).

![Main window](docs/screenshots/01-main.png)

## Screenshots

| Prayer times | Adhkar library |
|---|---|
| ![Prayer times](docs/screenshots/01-main.png) | ![Adhkar categories](docs/screenshots/02-adhkar-grid.png) |

| Morning adhkar | Settings |
|---|---|
| ![Morning adhkar](docs/screenshots/03-adhkar-dialog.png) | ![Settings](docs/screenshots/04-settings.png) |

## Features

- **Prayer Times** — Accurate calculation (MWL, Umm Al-Qura, Egyptian, Tunisian + 22 more), per-prayer icons, live countdown, Hijri date
- **Audio Azan** — Streaming MP3 playback with fade-in, volume control, multiple muezzins + per-prayer audio, takbeer mode
- **Adhkar Library** — 140 structured categories (382 remembrances) with repetition counts and source references, Arabic-Indic numerals
- **System Tray** — Mosque icon, next-prayer tooltip, show/quit menu, optional visibility, no-ghost quit
- **DND Integration** — Auto system-wide do-not-disturb around prayer times (GNOME)
- **Themes** — Dark/Light/Ottoman Gold/Catppuccin + auto, per-component palettes
- **Multi-language** — 17 languages with RTL support and live switching
- **Custom Offsets** — Per-prayer minute adjustments, madhab choice, high-latitude rule
- **City Search** — Virtual-scrolled picker (241 countries, 9000+ cities) with validation
- **Display Backend** — OpenGL/software render selection for GPU-less systems
- **Single Instance** — Second launch notifies instead of duplicating audio

## Requirements

- Python 3.10+
- PySide6 (Qt6), adhan, miniaudio
- Linux with PulseAudio/PipeWire for audio; `notify-send` optional (tray fallback built in)

## Installation

Download the AppImage from the releases page, make it executable and run it:

```bash
chmod +x Athan-Five-Times-x86_64.AppImage
./Athan-Five-Times-x86_64.AppImage
```

> The AppImage runs on the host Python: it needs PySide6 + adhan +
> miniaudio installed on your system (it tells you exactly what is
> missing instead of crashing). Install Qt via your distro, then
> `pip install --break-system-packages adhan miniaudio`.

Or install a native package (also on the releases page):

```bash
# Debian / Ubuntu (Qt wheels exist on Debian 13 / Ubuntu 25.04+)
sudo dpkg -i athan-five-times_0.3.15b_all.deb
sudo apt-get install -f   # pulls python3-pyside6* if missing
pip install --break-system-packages adhan miniaudio
athan-five-times

# Fedora / openSUSE (from spec)
sudo dnf install athan-five-times-0.3.15b-1.noarch.rpm

# Arch Linux (from PKGBUILD)
makepkg -si   # inside packaging/arch, or use the AUR
```

Or run from source:

```bash
pip install -r requirements-lock.txt
./run.sh
```

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/          # 407 tests
python3 scripts/smoke-qml.py     # QML zero-error gate
python3 scripts/e2e-features.py  # isolated end-to-end (44 checks)
```

`AppDir/` is derived build staging — regenerate with `bash scripts/sync-appdir.sh`
(CI regenerates it, verifies with `--check-only`, then runs the QML smoke gate).

Native packages live under `packaging/`:

```bash
bash packaging/debian/build-deb.sh        # needs dpkg-deb → .deb
bash packaging/rpm/build-rpm.sh           # needs rpmbuild → .rpm
cd packaging/arch && makepkg -si          # Arch
```

## الخصوصية / Privacy

عند التشغيل الأول فقط يحاول التطبيق تخمين مدينتك عبر بحث IP
‏(`ip-api.com` ثم `ipapi.co` ثم `ipinfo.io`) لضبط الموقع مسبقاً. لا حسابات،
لا تتبع، ولا أي استخدام آخر للشبكة. يمكنك تغيير المدينة في أي وقت
من الإعدادات ← الموقع، أو إعادة الضبط للافتراضي من
الإعدادات ← إدارة الإعدادات، أو البقاء دون إنترنت للإبقاء على اختيارك الحالي
(مكة عند التشغيل الأول فقط).
يُحفظ الموقع المكتشف تلقائياً في كاش محلي لمدة 24 ساعة فقط
(`~/.cache/prayer-times/location.json`)، ويُمسح عند تغيير المدينة يدوياً.

On first run only, the app attempts one IP-geolocation lookup (`ip-api.com`,
then `ipapi.co`, then `ipinfo.io`) to preset your city. No accounts, no
tracking, no other network use. Change the location anytime in
Settings → Location, reset to defaults in Settings → Manage Settings,
or stay offline to keep your current choice (Mecca on first run only).
The auto-detected location is cached locally for 24h only
(`~/.cache/prayer-times/location.json`) and cleared on manual city change.

## License

See [LICENSE](LICENSE). Third-party credits: **عن البرنامج** dialog in the app.

# Third-party assets

## Fonts (SIL Open Font License 1.1)

- **Cairo** (Regular, Bold) — Google Fonts, OFL-1.1
- **IBM Plex Sans Arabic** (Regular, Light, Bold) — Google Fonts, OFL-1.1

Full license texts: https://openfontlicense.org (OFL-1.1).

## Azan recordings (`assets/muezzins/`)

Bundled MP3s are recordings of well-known muezzins, downloaded from an
open GitHub source. Per the project owner they are free and require no
license for this use:

- قطامي (Qatami), Nasser Alqatami, Malek Chebae, Ibrahim Al-Arkani,
  Majed Al-Hamathani, Mansoor Az-Zahrani, Hamad Deghreri,
  Abed Albase, Athan Hamdan Almalki, Athan Suhaib Khatba,
  Mohammad Almenshawy, Ahmad Nuyne, Farouk Abdallah

The app plays whatever MP3s are present in `assets/muezzins/` (or user-added
muezzins); deleting files only removes those voices.

## Icons

Prayer, adhkar-category and tray icons are rendered from the project's own
Dart sibling (` PrayerIcon ` painters) — no third-party icon sets.

## Adhkar content

Remembrance texts (adhkar) belong to no one: they are divine religious
teachings for everyone and require no license or attribution.

For the record, the library (`assets/adhkar/`, 140 categories / 382 items)
was assembled from commonly circulated collections (project's own assets
plus open adhkar data, 345 rows); identical texts were deduplicated.
Where sources disagree on repetition counts, our kept variant is documented
in code comments; texts without an explicit count default to 1.

## Code libraries

See the in-app **About** dialog and `LICENSE` (MIT): Python (PSF),
Qt 6 + PySide6 (LGPL-3.0), miniaudio (MIT), Adhan (MIT), cffi (MIT),
pycparser (BSD).

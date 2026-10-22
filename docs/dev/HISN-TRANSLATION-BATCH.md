# Handoff — Hisn al-Muslim translation batches (adhkar library)

> **Purpose:** durable state for a session that may be restarted. Everything below was
> verified in-repo on the working tree as of the last session (no commit was made).
> Read this file first, then `git status` / `git diff --stat`, before touching anything.

---

## 1. What is done (current state)

**Library size:** 361 items across 23 categories (+ `index.json`) = 24 JSON files in
`assets/adhkar/`. Matches the docstring in `backend/adhkar_repo.py:2`.

**Hisn batch (this work stream):** the Hisn al-Muslim morning/evening set, stored as
**51 item ids / 33 unique texts** in `morning.json` + `evening.json` (the evening wording is a
separate item id, so one dhikr can appear as two ids). Coverage is therefore given as
`ids/51` and `unique/33`.

| Language | ids | unique | Source |
|---|---|---|---|
| `ar` (source) | 51/51 | 33/33 | repo |
| `en` | 51/51 | 33/33 | hisnmuslim.com + HadeethEnc |
| `es`, `es_la` | 51/51 | 33/33 | hisnmuslim.com (`es_la` = byte-identical mirror) |
| `fr` | 51/51 | 33/33 | IslamHouse French PDF + Osoul AR-FR edition |
| `hi` | 51/51 | 33/33 | hisnmuslim.com |
| `id` | 51/51 | 33/33 | hisnmuslim.com |
| `it` | 51/51 | 33/33 | IslamHouse Italian DOCX |
| `ms` | 51/51 | 33/33 | archive.org `ms_hisn_muslim` (OCR text layer) |
| `ru` | 51/51 | 33/33 | IslamHouse Russian DOCX |
| `tk` | 51/51 | 33/33 | IslamHouse Turkmen DOCX |
| `tr` | 51/51 | 33/33 | archive.org `tr_Hisnul_Muslim.pdf` (İsmail Yaşa) |
| `de` | 33/51 | 21/33 | qabasi.com/de (**+9 ids** this stream) |
| `ur` | 33/51 | 21/33 | qabasi.com/ur + HadeethEnc 6093/3008 (**+9**) |
| `so` | 39/51 | 25/33 | hisnmuslim.com/i/so (**+15**) |
| `pa` | 26/51 | 17/33 | HadeethEnc 6093 (**+2**) |
| `ps` | 24/51 | 16/33 | pre-existing only (**+0**) |

⇒ **716 translation entries** (444 distinct texts) across the 16 non-Arabic locales;
**11 non-Arabic languages have full 33/33 coverage.** The 5 partial locales already had
24 ids each from earlier i18n work; this stream added the `+N` ids shown above.

Note: `pa` = **Punjabi** (Gurmukhi, U+0A00 block) and `ps` = **Pashto** (Perso-Arabic);
they are distinct locales — do not swap them.

**Other translation sets (untouched by this work stream)**

| Set | Items | Languages |
|---|---|---|
| `morning.json` legacy + Qur'an batch | 12 | all 17 |
| `evening.json` legacy + Qur'an batch | 12 | all 17 |
| `after_prayer.json` (pilot) | 12 | all 17 |

**Where the state lives**

- `assets/adhkar/{morning,evening}.json` → `translation_meta.hisn_batch`:
  - `languages` — languages with **full** 27/27 coverage
  - `partial_languages` — `{lang: [item ids]}` for partial coverage
  - `missing_languages` — languages with **no** coverage
  - `items`, `sources` (per language), `source`, `note`
  - plus `translation_meta.partial_items`, `covered_items`, `verification_status`, `known_gaps`
- `tests/test_adhkar_repo.py` → class `TestMorningEveningHisnPartialBatch`
  - `LANGUAGES` = full-coverage languages
  - `PARTIAL` = `{lang: {"morning": {...}, "evening": {...}}}` — mirrors the JSON metadata
  - `ARABIC_SCRIPT_LANGS = ("ur", "ps")` — skipped by the no-Arabic-script check
    (Urdu/Pashto legitimately use the Arabic script; same rule as
    `backend/translations/__init__.py:_ARABIC_SCRIPT_LANGS`)

**Gates last run (all green)**

```
python3 -m pytest tests/ -q          # 562 tests in tests/ (56 in test_adhkar_repo.py), 0 failures
python3 -m ruff check backend/ tests/ # clean (CI only lints these two dirs)
python3 -m json.tool assets/adhkar/morning.json   # valid
python3 -m json.tool assets/adhkar/evening.json   # valid
QT_QPA_PLATFORM=offscreen python3 scripts/smoke-qml.py   # SMOKE OK: zero QML errors
```

**Working tree:** modified files, **not committed**. Split into thematic commits when
committing: (1) adhkar JSON translations, (2) `translation_meta`, (3) tests,
(4) backend/translations + `backend/adhkar_repo.py` + `qml/*` + `scripts/e2e-features.py`
(pre-existing session edits).

---

## 2. Extraction map (the key to finishing the remaining languages)

`hisnmuslim.com` page-1 block index → repo ID. The Arabic book number of Hisn al-Muslim
equals **page-1 block index + 75**.

| Repo ID | Arabic book no. | Source | Adaptation needed |
|---|---|---|---|
| `m03` / `e07` | 86 | `/i/<lang>/1` block 11 | none |
| `m04` / `e08` | 87 | `/i/<lang>/1` block 12 | Arabic = **رسولًا**: it/ru/tk use *Messenger*, es uses *Mensajero*, de/ur/tr/ms use *Rasul/Rassul* |
| `m05` | 256 | `/i/<lang>/130` block 2 (PDF) or label `(256)` (books) | dhikr is quoted inside a narration → extract the quoted dhikr only |
| `m08` / `e09` | 82 (part 1) | `/i/<lang>/1` block 7 (first half) | none |
| `mor17` / `eve16` | 90 | `/i/<lang>/1` block 15 | evening form (source often morning-only) |
| `mor18` / `eve17` | 82 (part 2) | `/i/<lang>/1` block 7 (second half) | none |
| `mor19` / `eve18` | 84 | `/i/<lang>/1` block 9 | none |
| `mor20` / `eve19` | 88 | `/i/<lang>/1` block 13 | none |
| `mor21` / `eve20` | 89 | `/i/<lang>/1` block 14 | evening form |
| `mor22` / `eve21` | 85 | `/i/<lang>/1` block 10 | none |
| `mor25` / `eve24` | 203 | `/i/<lang>/92` block 0 | Arabic is plural → adapt singular→plural |
| `mor26` / `eve25` | 120 | `/i/<lang>/34` block 1 | none |
| `mor27` / `eve26` | 250 | `/i/<lang>/129` block 2 | dhikr quoted inside a narration |
| `mor29` | 95 | `/i/<lang>/1` block 20 | none |
| `e03` | 77 (evening) | `/i/<lang>/1` block 2 | evening form (source may be morning-only) |

**Evening forms to adapt** (Arabic swaps morning→evening words):
`e03` (أمسينا … هذه الليلة), `eve16` (أميت على الفطرة), `eve20` (أمسينا … هذه الليلة).

### 2.1 IMPORTANT METHOD NOTE — never copy text out of tool output

While building this batch, text read from tool output was silently mangled at least once
(one Arabic-script word in the Malay payload was replaced by an unrelated 8-character
token) and the corrupted string ended up in a payload. Recovery was
possible only because the payload was re-verified against the source.

**Rules that worked:**
1. Extract source strings **programmatically** (Python reads the file/URL and writes the
   payload). Never retype/copy text you only saw in a terminal dump.
2. Verify every payload with a vocabulary check: each word must exist in the source file's
   word list; anything else is either an intentional adaptation or corruption.
3. For PDF/OCR sources, prefer `-raw` extraction (reading order) over `-layout`
   (two-column PDFs interleave columns and break naive pairing).
4. Use `assert token in text` inside the builder so a missing token fails loudly instead
   of silently producing a partial translation.

Helper scripts used (recreate them in `/tmp` if needed, they are not in the repo):
`apply_lang.py` (merge + metadata), `verify_payload.py` / `check_words.py` (validation),
`build_ms.py` / `build_so.py` (per-language builders), `qabasi_map.py` (qabasi.com parser).

---

## 3. Sources verified for the remaining languages

### 3.1 hisnmuslim.com — the best structured source

Available language slugs (from the homepage): `ar, bn, bs, en, es, fa, ha, hi, id, pt,
so, sw, th, yo, zh`. ⇒ among the missing languages only **`so`** is served.

`so` gaps (measured): `/i/so/1` block 7 has no Somali (only the note "waxaa la dhahaa
seddex jeer") → `m08`/`e09`/`mor18`/`eve17` missing; `/i/so/92` (mor25) and `/i/so/129`
(mor27) and `/i/so/130` (m05) have no Somali; the evening wording of `e03`, `eve16`,
`eve20` is not given (only the morning text) ⇒ `so` currently covers 15 items.

### 3.2 IslamHouse — book id 1566, per-language download files

Book pages are `https://islamhouse.com/<lang>/books/1566/`; the file link follows
`https://d1.islamhouse.com/data/<lang>/ih_books/single/<file>`.

* **fr** → `https://d1.islamhouse.com/data/fr/ih_books/single/fr-fortress-of-the-muslim.pdf`
  (12.6 MB, text layer ✔). Other language slugs (`de`, `tr`, `ur`, `ps`, `pa`, `so`, …)
  redirect to the homepage ⇒ **no edition of book 1566 for them**.
* `it`, `ru`, `tk` were used earlier from IslamHouse DOCX files
  (`it-fortezza-del-musulmano-finale.docx`).

### 3.3 Osoul bilingual AR-FR edition (GitHub)

`https://github.com/Kiwifu/la-citadelle-du-musulman` → `La_Citadelle_du_Musulman_AR-FR.md`
(208 KB). Item markers are `**NN.**`, then `> «Arabic»`, `*transliteration*`, the French
paragraph, then `— *source*`. Covers ~15 of our items (no `mor17/mor18/mor25/mor26`, no
evening forms) — the PDF (`fr-fortress-of-the-muslim.pdf`) covers the rest.

### 3.4 archive.org

| Item | Files | Use |
|---|---|---|
| `Hisn_Almuslim_collection` | `tr_Hisnul_Muslim.pdf` (1.1 MB ✔ text), `tk_…pdf`, `en_…doc`, `fa_…docx` | Turkish ✔ |
| `ms_hisn_muslim` | `ms_hisn_muslim.pdf` (scanned, no text layer) + `ms_hisn_muslim_djvu.txt` (OCR, **Malay OCR is good**) | Malay ✔ |
| `HisnUlMuslimUrdu` | PDF scanned; `_djvu.txt` = **Urdu OCR is unusable** (letterforms conflated) | ✘ |
| `hisn_ul_muslim_urdu_202609` | 55 MB PDF, 1.2 kB text layer ⇒ scanned | ✘ |
| `hisn-ul-muslim-sahih` | Urdu sahih edition (OCR only) | ✘ |
| `hisn-al-muslim-kinga ya muislamu…` | Swahili | not an app language |

### 3.5 qabasi.com — German and Urdu

`https://qabasi.com/<lang>/athkar/morning|evening` for `ar, bn, de, en, fa, fr, id, ms,
tr, ur`. Structure (per item, `div.p-5`): `p[0]` Arabic, `p[1]` transliteration, `p[2]`
translation; labels differ per language (`Umschrift`/`Übersetzung`, `Okunuş`/`Çeviri`,
`Transliterasi`/`Terjemahan`). Only **10 curated items per page** (Ayat al-Kursi, the
three Quls, Sayyid al-Istighfar, Allahumma afini, Hasbiyallah + a few morning du’as) ⇒
a full scan of all six sections (morning, evening, sleep, wake-up, after-prayer, wudu =
35 boxes) matches only **5 unique dhikkar (9 ids)**. Several dhikkar are bundled into one
box, so the boxes cannot be split per item. Urdu writes in the Arabic script.

### 3.6 HadeethEnc API (partial coverage, all 8 remaining languages supported)

```
https://hadeethenc.com/api/v1/hadeeths/one/?language={lang}&id={id}
```
`https://hadeethenc.com/api/v1/languages/` lists `fr, de, tr, ur, ps, so, pa, ms, it, …`.
Measured by matching the repo Arabic against HadeethEnc's `ar` text over ids
**5850–6800** (not assumed):

| hadith | maps to | used for | note |
|---|---|---|---|
| `6093` | `m03` / `e07` | `pa` (m03/e07), `de` (m03) | works: quoted Arabic + parenthetical translation |
| `3008` | evening set (`e03`, `mor19`, `mor20`, `mor21`, `eve16`, `eve18`, `eve19`, `eve20`) | `ur` (e03) | **404** in the `pa`/`ps` editions |
| `6272` | `m04` / `e08` | — | **rejected**: the text is the longer adhan-reply narration (shahada + رضيت…), not the short dhikr |
| `65906` | — | — | **not** m04/e08; its quoted anchor is `بسم الله الرحمن الرحيم` |

Only these two hadiths in the whole range contain any of the still-missing dhikkar, so
probing more ids is not worth it.

**How the localised text is extracted (worked):** the Arabic inside the localised text is
the anchor. Two shapes occur:
* quoted Arabic (`"…"`, `«…»`, `„…“`) → the translation is the text right after the
  closing quote (used for `ur` 3008/6093);
* transliteration + parenthesised translation (`„Bismillahi-…“ (Mit dem Namen Allahs, …)`)
  → the parenthetical is the translation (used for `de` 6093, `pa` 6093).

**Pashto (`ps`) has no extractable shape**: the edition is narration → `«Arabic dhikr»` →
`«Pashto transliteration + Arabic dhikr»`, i.e. no standalone translation of the dhikr.
**Somali (`so`) has no HadeethEnc edition at all.**

Always strip punctuation **and** diacritics before comparing, then require a token-similarity
ratio ≥ 0.85; without punctuation stripping the same comparison silently returns 0 matches
(this bit us once), and with a low threshold a longer/different narration gets attached to
the wrong item.ition of book 1566 (pages redirect to the home page).
* archive.org search: no German / Pashto / Punjabi / Somali Hisn book.
* hisnmuslim.com: no `fr/de/tr/pa/ur/ps/ms` language slug.
* Search engines: DuckDuckGo HTML works (`https://html.duckduckgo.com/html/?q=…`) but
  rate-limits; Mojeek returns a captcha; the `websearch` tool may be blocked by a
  hidden-unicode filter.

---

## 4. How to merge one language (repeatable pattern)

`apply_lang.py` (in `/tmp/opencode/hisn/`) takes a payload JSON:

```json
{"lang": "fr", "source": "...", "morning": {"m03": "..."}, "evening": {"e03": "..."}}
```

and for each category: writes `translations[lang]`, keeps `translations["ar"] == arabic`,
asserts non-empty and no Arabic script (skipped for `ur`/`ps`), then updates
`hisn_batch.languages` / `partial_languages` / `missing_languages` / `sources` and
`translation_meta.verification_status`.

* **Full coverage** → the language goes into `hisn_batch.languages`.
* **Partial coverage** → add `"partial": true` to the payload; the language is recorded in
  `hisn_batch.partial_languages` as `{lang: [item ids]}` and removed from `languages`.

Then update `tests/test_adhkar_repo.py`:
* `LANGUAGES` += the language (full coverage only)
* `PARTIAL` += `{lang: {"morning": {...}, "evening": {...}}}`

Verify: `pytest tests/test_adhkar_repo.py -q`, `ruff check backend/ tests/`,
`python3 -m json.tool` on both JSONs, and the vocabulary check of the payload.

---

## 5. Remaining punchlist

1. **`ps`** — 24/51 ids pre-existing, **0 new**. HadeethEnc `6093`/`6272` exist but the
   Pashto edition gives only narration + transliteration (no standalone dhikr translation),
   so nothing can be harvested. Needs a Pashto Hisn book.
2. **`de` / `ur`** — 33/51 each (21/33 unique); 18 ids / 12 unique missing:
   `m04 m05 mor17 mor18 mor21 mor22 mor25 mor26 mor27 mor29 e08 eve16 eve17 eve20 eve21
   eve24 eve25 eve26`. qabasi's six sections are exhausted (5 unique dhikkar), HadeethEnc has
   no standalone translations for these ⇒ needs a full German/Urdu Hisn book.
3. **`so`** — 39/51 (25/33); 12 ids / 8 unique missing: `m05 m08 mor18 mor25 mor27 e03 e09
   eve16 eve17 eve20 eve24 eve26`. hisnmuslim's Somali edition (pages 1–135) has **no Arabic
   script** and no Somali text for `m05/m08/mor18/mor25/mor27`. Do not fabricate the evening
   wording of `e03`/`eve16`/`eve20`.
4. **`pa`** — 26/51 (17/33); 25 ids / 16 unique missing. HadeethEnc `6093` was the last usable
   source; `3008` is 404 in the Punjabi edition.
5. **Metadata note (fixed):** `hisn_batch.note` now spells out the Messenger terms
   (`en` Messenger, `es` **Mensajero**, `fr` Messager, `id` rasul, `tk` resul, `ru`
   посланник; `it` alone uses *Profeta*). The earlier claim that `es` used *Profeta* was
   wrong.
6. **`es_la` note:** `after_prayer.json` says *"es_la is a mirror of es"*. True for the
   adhkar content (63/63 items identical) but **not** for the UI: 10 of the 264 `ui` keys
   differ between `es.json` and `es_la.json`. Wording should be narrowed.
7. **Native review** — the adapted evening forms (`e03`, `eve16`, `eve20`), the
   singular→plural adaptation of `mor25`/`eve24`, and the Malay/Urdu/Somali OCR-derived
   texts were written by the assistant, not by native speakers. Flag them in
   `needs_review`.
8. **Scope decision** — 298 items in 19 categories have no non-Arabic translation.

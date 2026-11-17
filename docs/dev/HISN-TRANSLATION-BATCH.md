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
| `de` | 51/51 | 33/33 | IslamHouse German PDF (`de_Hisnul_ElMuslim.pdf`, book 247027) + HadeethEnc 6093 / qabasi.com/de for the legacy ids |
| `ur` | 51/51 | 33/33 | qabasi.com/ur + HadeethEnc + islambook.com/ur/azkr/1,2 (12 unique texts / 18 ids) |
| `so` | 51/51 | 33/33 | hisnmuslim.com/i/so + Somali book `so_Xisnul_Muslim.pdf` + hisnmuslim.com/i/so/1 (4 unique texts / 5 ids, evening forms adapted) |
| `pa` | 51/51 | 33/33 | HadeethEnc 6093 + islambook.com/pa/azkr/1,2 (16 unique texts / 25 ids, Gurmukhi) |
| `ps` | 51/51 | 33/33 | islambook.com/ps/azkr/1,2 (17 unique texts / 27 ids) |

⇒ **816 translation entries** (509 distinct texts) across the 16 non-Arabic locales;
**all 16 non-Arabic languages now have full 33/33 coverage.** Urdu, Punjabi and Pashto
were completed on 2026-11-17 from the islambook.com morning/evening pages; Somali gained
its last 4 unique texts from hisnmuslim.com/i/so/1. The only remaining work is native
review of the composed/adapted entries (`translation_meta.needs_review`).

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
  - `languages` — languages with **full** coverage of the batch ids (now 16/16)
  - `partial_languages` — `{lang: [item ids]}` for partial coverage; **empty** now that
    ur/pa/ps/so are complete (the key stays so readers can tell "none" from "not tracked")
  - `missing_languages` — languages with **no** coverage; **empty**
  - `items`, `sources` (per language), `source`, `note`
  - plus `translation_meta.partial_items`, `covered_items`, `verification_status`,
    `known_gaps`, `needs_review`
  - `partial_items` is **not** a coverage list: it marks membership in this batch (the
    test asserts every batch id is listed there and none is in `covered_items`).
  - `needs_review` — `{item id: [lang, …]}` for text composed/adapted by the assistant
    rather than copied from a published translation. Keep it until a native speaker signs off.
- `tests/test_adhkar_repo.py` → class `TestMorningEveningHisnBatch`
  - `LANGUAGES` = the 16 full-coverage locales
  - `PARTIAL = {}` — no per-item partial sets remain; the metadata key must stay empty
  - `NEEDS_REVIEW` — mirrors `translation_meta.needs_review` (`test_needs_review_flags`)
  - `ARABIC_SCRIPT_LANGS = ("ur", "ps")` — skipped by the no-Arabic-script check
    (Urdu/Pashto legitimately use the Arabic script; same rule as
    `backend/translations/__init__.py:_ARABIC_SCRIPT_LANGS`)
  - `test_full_batch_has_sources` — asserts empty `partial_languages`/`missing_languages`
    and a `sources` entry for ur/pa/ps/so in both categories

**Gates last run (all green)**

```
python3 -m pytest tests/ -q          # 564 tests in tests/ (58 in test_adhkar_repo.py), 0 failures
python3 -m ruff check backend/ tests/ # clean (CI only lints these two dirs)
python3 -m json.tool assets/adhkar/morning.json   # valid
python3 -m json.tool assets/adhkar/evening.json   # valid
QT_QPA_PLATFORM=offscreen python3 scripts/smoke-qml.py   # SMOKE OK: zero QML errors
git diff --check                     # clean (no whitespace errors)
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
| `mor26` / `eve25` | 121 | `/i/<lang>/34` block 1 | none |
| `mor27` / `eve26` | 250 | `/i/<lang>/129` block 2 | dhikr quoted inside a narration |
| `mor29` | 95 | `/i/<lang>/1` block 20 | none |
| `e03` | 77 (evening) | `/i/<lang>/1` block 2 | evening form (source may be morning-only) |

**Evening forms to adapt** (Arabic swaps morning→evening words):
`e03` (أمسينا … هذه الليلة), `eve16` (أميت على الفطرة), `eve20` (أمسينا … هذه الليلة).

**ur/pa/ps shortcut (2026-11-17):** the three locales do not need this map. The
islambook.com morning/evening pages use the same `zekr-N` ids across languages and already
contain the published translation for each block, so the mapping is
`zekr-9→m03/e07`, `zekr-5→m04/e08`, `zekr-223→m05`, `zekr-13→m08/e09`, `zekr-11→mor17`,
`zekr-14→mor18/eve17`, `zekr-15→mor19/eve18`, `zekr-16→mor20/eve19`, `zekr-17→mor21`,
`zekr-18→mor22/eve21`, `zekr-21→mor25/eve24`, `zekr-22→mor26/eve25`, `zekr-23→mor27/eve26`,
`zekr-313→mor29`, `zekr-30→e03`, `zekr-38→eve16`, `zekr-44→eve20`. See §3.8.

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
the wrong item.

### 3.7 Local reference-file audit (`New Folder/`, 2026-11-17)

The folder holds 20 PDFs = **16 unique files**; four are byte-identical duplicates present
as `… (1).pdf` (`de_Hisnul_ElMuslim`, `ps-fortress`, `ko-hisn-almuslim-in-korean`,
`risala_ur_hisnul_muslim`). Language was auto-detected from the text layer, not assumed from
the file name.

| File | Pages | Text layer | Detected language | Verdict for this batch |
|---|---|---|---|---|
| `de_Hisnul_ElMuslim.pdf` | 155 | ✔ 291 k chars | German | source of record; `de` already 51/51 |
| `en-fortress-of-the-muslim.pdf` | 204 | ✔ English + partial Arabic | English | `en` already 51/51 |
| `risala_fr_hisnulmuslim.pdf` | 197 | ✔ 310 k chars | French | `fr` already 51/51 |
| `tr_Hisnul_Muslim.pdf` | 99 | ✔ 305 k chars | Turkish | `tr` already 51/51 |
| `tr_Hisnul_Muslim_1436_1.pdf` | 121 | ✔ | Turkish | alternate edition, not needed |
| `risala_tr-hisnul_muslim.pdf` | 159 | ✔ | Turkish | alternate edition, not needed |
| `pt-fortificac-o-do-muculmano.pdf` | 202 | ✔ | Portuguese | **not an app language** |
| `ko-hisn-almuslim-in-korean.pdf` | 148 | ✔ Hangul | Korean | **not an app language** |
| `risala_bn_hisn_almuslim.pdf` | 147 | ✔ Bengali | Bengali | **not an app language** |
| `risala_bn-hisnul_muslim.pdf` | 208 | ✔ Bengali | Bengali | alternate edition, same |
| `so_Xisnul_Muslim.pdf` | 236 | ✔ 257 k chars | Somali | **used**; all 7 merged payloads reproduce at word coverage 1.000 |
| `risala_ur_hisnul_muslim.pdf` | 155 | partial | Urdu | **not usable** (below) |
| `ur_Hisnul_Muslim.pdf` | 128 | ✘ 2.5 k chars | Urdu | scanned/outlined |
| `ur_Hisnul_Muslim_1436.pdf` | 172 | ✘ 0.9 k chars | Urdu | scanned |
| `ps-fortress.pdf` | 152 | partial | Pashto | **not usable** (below) |

**Why the Urdu and Pashto books cannot be harvested.** Both number 152 items (short edition,
so no 203/250/256) and both expose a text layer, but that layer is **not the dhikr
translations**:

* no Hisn translation can avoid the word Allah, yet in the Pashto file `الله` occurs **0**
  times in 156 k chars (its most frequent token is the scrambled form `اهلل`) and the
  ordinary words `لمونځ` (prayer) and `دعا` are absent; in the Urdu file `اللہ` occurs 5
  times (plus 146 visually reversed `هللا`) in 146 k chars;
* the RTL glyphs are stored in visual order **and inconsistently** (reversing every line
  turns 794 `کے` into 210 and drops `اللہ` to 0), so no single transform restores logical
  order;
* the content words of item 86 itself (`نام`, `زمین`, `آسمان`, `نقصان`) are absent from its
  block, and across the 145 items shared by the two books the block lengths correlate
  **negatively** (r = −0.22) where a correct alignment would be strongly positive.

The translation bodies are set as images. The two `ur_Hisnul_Muslim*.pdf` scans have no text
layer at all (`pdftotext` yields 2.5 kB over 128 pages and 0.9 kB over 172 pages). Do **not**
extract these books by item number: the numbering is standard, but the text under each number
is not a safely readable translation.

**No Punjabi source exists in this folder**: none of the 20 files is Punjabi
(`risala_bn*` is Bengali), and a workspace-wide `find` returns no other PDF.
*(Superseded: the online islambook.com pages of §3.8 later supplied `pa` in full.)*

Net effect at audit time: the new reference files add **no** extractable Hisn items; `ur`
stayed at 33/51 and `ps` at 24/51. *(Superseded by §3.8 for both: ur 51/51, ps 51/51.)*

**Online sources checked (2026-11-17):**

* **Urdu — archive.org `HisnUlMuslimUrdu`** (Saeed bin Ali al-Qahtani, 79-page scan). It has
  a real OCR text layer (251 kB, tesseract `urd`) and is genuine Urdu prose (`کے` 725, `سے`
  678, `ہے` 324), but it is too corrupt for payloads: `زمین` and `نقصان` occur **0** times in
  147 k chars, item 86's block lacks its content words, and the text around the Allah
  formula is garbled. Three other Urdu OCR copies were measured and are equally partial or
  garbled: `hisn-ul-muslim-sahih` (104 kB), `HisnUlMuslimTahqeeqOTakhreejZubairAliSb`
  (142 kB) and `hisnullmuslim` (145 kB). Rejected.
* **Pashto — archive.org `20260309_20260309_0532`** (Hisn al-Muslim in Pashto, 275 kB OCR,
  tesseract `pus`). It is readable and really does contain the dhikr translations — item 86
  reads `د هغه الله په نوم چې … په ځمکه او آسمان کې ضرر نه رسوي …` — but it is a **commentary
  edition**: Arabic transliteration, hadith footnotes and explanatory prose are interleaved
  with the translations, and its 106 `#` and 33 `ترجمه` separators also occur inside
  footnotes and Qur'an quotations. OCR noise is present (e.g. a bare `ه` where `هغه` is
  meant). Not merged automatically; this is the best candidate for a native Pashto reviewer.
* **IslamHouse alternate editions (2026-11-17)**: book 1566 has no Urdu/Pashto file, but
  other ids do. `ur/books/1584` serves `ur_Hisnul_Muslim.pdf` (129 pp) and
  `ur_Hisnul_Muslim_1436.pdf` (173 pp) — both **scans** (`pdftotext` yields 2.6 kB / 0.9 kB);
  its `ur-fortress.pdf` (174 pp) has 409 k chars, but the layer is fragmented RTL (16 468
  `U+202C`, 9 933 `U+202B`, 4 862 `U+202A`; words are split and character-reversed
  inconsistently: `کے` 203 raw → 846 after line reversal, while `اللہ`, `زمین` and `نقصان`
  stay at 0 under every transform). `ur/books/2846918` is the same
  `risala_ur_hisnul_muslim.pdf` already audited. `ps/books/727736` serves
  `ps_hisn_almuslim.pdf` (302 pp) with **no text layer** (302 chars). No `.docx`/`.doc`
  endpoint exists for any of them (all 404).
* **Pashto structural pilot (archive.org OCR)**: the OCR alternates Arabic lines (no
  Pashto-specific letters) with Pashto translation lines, so line classification itself is
  reliable. Anchoring the 20 testable batch ids (11 unique) by their Arabic text gave only
  **one** complete translation (`m03`/`e07`); 8/20 best matches scored r = 0.37–0.66 and came
  from hadith footnotes/commentary, and even the clean item contains the systematic OCR
  substitution `هغه` → `څه`. Not merged; this OCR is only usable by a native reviewer.
* **Punjabi**: no Hisn book found on archive.org or GitHub (`hisn punjabi`, `hisn pashto`
  repository searches return 0) ⇒ `pa` stays blocked.

**Sources checked and rejected:**

* IslamHouse: no edition of book 1566 for the remaining languages (pages redirect to the
  home page).
* hisnmuslim.com: no `fr/de/tr/pa/ur/ps/ms` language slug.
* Search engines: DuckDuckGo HTML works (`https://html.duckduckgo.com/html/?q=…`) but
  rate-limits; Mojeek returns a captcha; the `websearch` tool may be blocked by a
  hidden-unicode filter.

### 3.8 islambook.com — published Urdu / Punjabi / Pashto morning & evening (found 2026-11-17)

This is the source that closed `ur`, `pa` and `ps`. Rejected alternatives failed because
they had no standalone dhikr text; islambook has one translated block per dhikr, for all
17 batch texts, in all three languages.

* **Pages:** `https://www.islambook.com/{ur,pa,ps}/azkr/1` (morning) and `/azkr/2`
  (evening). The pages are static HTML; `curl` gets **403**, a real browser loads them.
* **Anchors:** every dhikr is `<section id="zekr-N" class="azkar-entry">`, and `N` is
  **identical across the three languages**, so one item mapping serves all of them.
* **Text:** inside the section,
  `div.azkar-text[lang="ar"]` = Arabic, `div.azkar-translation[lang="ur|pa|ps"]` = the
  published translation. (`div.azkar-transliteration[lang=…]` holds transliterations for
  ~30 languages and is not used; the `[lang]` attribute is the reliable selector, not the
  element class.)
* **Punjabi script:** islambook's `pa` blocks are **Gurmukhi** (U+0A00–U+0A7F), which is
  what the app's `pa` locale requires. Assert this before merging: Gurmukhi present, no
  Arabic-script and no Latin characters in the payload.
* **Extraction:** run the pages in the browser, evaluate one JS snippet that walks the
  `zekr-N` ids and reads `innerText` of both divs, then `POST` the result to a local
  receiver (`127.0.0.1:8765`) that merges it into `ingested.json`. This keeps the text out
  of tool output entirely (see §2.1).
* **Verification:** for each mapping, assert that the app's normalized Arabic (harakat and
  punctuation stripped) is contained in the source `azkar-text[lang=ar]`. Three exception
  cases are handled explicitly, not silently:
  * `zekr-5` (`m04/e08`) orders *Allah–Islam–Muhammad* and says **نبيا** where the repo
    Arabic says **رسولًا** — the published translations were adapted to *Messenger* and to
    the repo's word order, then flagged `needs_review`.
  * `zekr-223` (`m05`) contains only the first half (**سبحان الله وبحمده**); the second
    half (**سبحان الله العظيم**) was appended by analogy and flagged.
  * `zekr-22` (`mor26/eve25`) has two typos in its source Arabic (around **ضلع** and
    **غلبة**); the published translations nevertheless render the repo's
    *غلبة الدين وقهر الرجال* correctly, so the check uses keyword tokens instead of the
    full string.
* **Numbers:** ur 17 texts / 18 ids, pa 17 / 25, ps 17 / 27 (some ids share a text, e.g.
  `m03`/`e07`). Only `m05` (all three) and `m04`/`e08` (all three) needed adaptation.

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

The coverage work is **done**: all 51 Hisn ids have a translation in all 16 non-Arabic
locales (816 entries / 509 distinct texts). What remains is review, not retrieval.

1. **Native review (the only real blocker).** `translation_meta.needs_review` lists every
   entry that was composed or adapted rather than copied from a published translation:
   * `m04` / `e08` in `ur`, `pa`, `ps`, `so` — published text says *نبي* and orders
     Allah–Islam–Muhammad; adapted to the repo's *رسولًا* and Allah–Muhammad–Islam.
   * `m05` in `ur`, `pa`, `ps`, `so` — islambook/hisnmuslim publish only the first half;
     the second half (*سبحان الله العظيم*) was appended.
   * Somali evening forms `e03`, `eve16`, `eve20`, `eve26` — derived from the published
     morning wording with the book's own morning→evening substitutions.
   * `mor27` (so) — the published Somali covers the short istighfar; the repo uses the long
     form, which was expanded.
2. **`m02` / `e02` preamble (resolved 2026-11-17).** The Arabic used to prepend the
   isti'adha (*أعوذ بالله من الشيطان الرجيم*) while the aft11 translations start at the ayah.
   The preamble was removed from both the Arabic and `translations.ar`, so the item is now
   exactly Ayat al-Kursi and matches all 16 translations; `reference_detail` is
   *البقرة: 255* and `test_kursi_has_no_istiadha_preamble` locks this in. If the isti'adha
   is wanted back, it must be added together with a translated form in every locale
   (option B: isti'adha + basmala + ayah).
3. **Verification already in place.** `tests/test_adhkar_repo.py::TestMorningEveningHisnBatch`
   asserts: full 16-language coverage of every batch id, empty `partial_languages` /
   `missing_languages`, a `sources` entry for ur/pa/ps/so, no Arabic script in `pa`/`so`,
   and exact agreement between `needs_review` and `NEEDS_REVIEW`. `git diff` shows the only
   changed translation values are the fills plus one Somali word (`nabinimo` →
   `rasuulnimo`).
4. **`es_la` note:** `after_prayer.json` says *"es_la is a mirror of es"*. True for the
   adhkar content (63/63 items identical) but **not** for the UI: 10 of the 264 `ui` keys
   differ between `es.json` and `es_la.json`. Wording should be narrowed.
5. **Scope decision (out of this stream).** 298 items in 19 categories have no non-Arabic
   translation at all; only the morning/evening Hisn batch was in scope here.
6. **Commit split (when asked):** (1) adhkar JSON translations + `translation_meta`,
   (2) tests, (3) this document, (4) pre-existing session edits
   (`backend/translations` + `backend/adhkar_repo.py` + `qml/*` + `scripts/e2e-features.py`).

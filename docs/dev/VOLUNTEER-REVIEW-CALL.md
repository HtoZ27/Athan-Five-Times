# Volunteer call — native review of the Hisn translations

Ready-to-publish text for a pinned GitHub issue. **Publish only after the branch
containing `docs/dev/HISN-REVIEW-QUEUE.md` is on `main`**, otherwise every link
below returns 404.

| Field | Value |
|---|---|
| Title | `Help wanted: native review of 17 Hisn al-Muslim translations (Urdu, Punjabi, Pashto, Somali)` |
| Labels | `help wanted`, `translations`, `good first issue` |
| Pin | yes |
| Milestone | none |

Copy everything from `## Context` down into the issue body.

---

## Context

AthanFiveTimes is a free, open-source (MIT) Linux prayer-times and adhkar app.
The morning and evening adhkar from *Hisn al-Muslim* are now translated into all
16 non-Arabic locales: 51 items, 816 localized strings.

All but 17 of those strings are copied from published translations. The
remaining 17 had to be composed or adapted during the translation work (with AI
assistance), because the published source was incomplete or used a different
Arabic wording. Each one is listed in the review queue with its Arabic, current
translation, source and the reason it is flagged.

**We need native speakers to confirm or correct them. No coding is required.**

## What needs review

| Language | Script | Entries | Items |
|---|---|---|---|
| Urdu (`ur`) | Arabic | 3 | `m04`, `m05`, `e08` |
| Punjabi, Gurmukhi (`pa`) | Gurmukhi | 3 | `m04`, `m05`, `e08` |
| Pashto (`ps`) | Arabic | 3 | `m04`, `m05`, `e08` |
| Somali (`so`) | Latin | 8 | `m04`, `m05`, `mor27`, `e03`, `e08`, `eve16`, `eve20`, `eve26` |

`m04` and `e08` share the same text, as do `mor27` and `eve26`.

**Partial reviews are welcome.** One item, one language, or a single comment is
useful; you do not have to review everything.

## Why these entries are flagged

- **`m04` / `e08`** — the published source says **نبي** ("prophet") and orders
  *Allah–Islam–Muhammad*; the app follows the Arabic **رسولًا** ("Messenger")
  and the order *Allah–Muhammad–Islam*. Please check that the translation says
  "Messenger" and follows that order. The Somali text also still carries the
  narration wrapper (*qofkii yiraahda…*); say whether it should be trimmed down
  to the dhikr itself.
- **`m05`** — the published source has only the first half
  (**سبحان الله وبحمده**); the second half (**سبحان الله العظيم**) was appended
  in the same register.
- **`mor27` / `eve26` (Somali)** — the published Somali covers the short
  istighfar; the app uses the long form (**العظيم الذي لا إله إلا هو الحي
  القيوم**), which was expanded.
- **`e03`, `eve16`, `eve20` (Somali)** — only the morning wording is published.
  The evening forms were derived with the book's own substitution rule
  (`waan waabariisanay` → `Waan galabaysanay`, `maalintan` → `habeenkan`, with
  the matching gender agreement: `fatxigeeda` → `fatxigiisa`, …). Please check
  grammar, agreement and natural phrasing.

## How to help

### Option A — comment only (no Git)

1. Open the review queue:
   [`docs/dev/HISN-REVIEW-QUEUE.md`](https://github.com/HtoZ27/Athan-Five-Times/blob/main/docs/dev/HISN-REVIEW-QUEUE.md)
2. For each entry, compare the Arabic, the current translation and the source.
3. Reply on this issue with the template below.

```text
Language: so
Items reviewed: m04, m05
Verdict: approved
```

For a correction, quote the current text and give the replacement:

```text
Language: so
Item: m04
Current: <copy the text from the queue>
Suggested: <your replacement>
Reason (optional): <grammar, register, meaning>
```

You do not need perfect formatting. A plain comment in your language is enough.

### Option B — pull request

```bash
git clone https://github.com/HtoZ27/Athan-Five-Times.git
cd Athan-Five-Times
```

Then, in [`assets/adhkar/morning.json`](https://github.com/HtoZ27/Athan-Five-Times/blob/main/assets/adhkar/morning.json)
or [`evening.json`](https://github.com/HtoZ27/Athan-Five-Times/blob/main/assets/adhkar/evening.json):

1. Update `items[].translations["<lang>"]` with your text.
2. Remove `<lang>` from `translation_meta.needs_review["<item>"]` for every
   entry you have signed off.
3. Mirror the same change in `NEEDS_REVIEW` in
   [`tests/test_adhkar_repo.py`](https://github.com/HtoZ27/Athan-Five-Times/blob/main/tests/test_adhkar_repo.py).
4. Run the checks:

```bash
python3 -m pytest tests/test_adhkar_repo.py -q
python3 -m json.tool assets/adhkar/morning.json > /dev/null
python3 -m json.tool assets/adhkar/evening.json > /dev/null
```

Open the pull request against `main`. If you have not set up the project yet,
follow [`CONTRIBUTING.md`](https://github.com/HtoZ27/Athan-Five-Times/blob/main/CONTRIBUTING.md)
first. If a command fails and you are not sure why, push the branch anyway and
ask in the pull request; we will help.

## Review checklist

- [ ] The meaning matches the Arabic; nothing added or omitted.
- [ ] The phrasing is natural in the target language, not a literal calque.
- [ ] Religious terms match the rest of the app.
- [ ] The register matches the published Hisn text already in the app.
- [ ] `pa` stays in Gurmukhi script (not Shahmukhi).
- [ ] Only the flagged language and entries are touched.

## Scope

- The Arabic text is the source of truth; this is a language review, not a new
  religious ruling or a re-translation of the whole app.
- Until an entry is signed off it stays in `needs_review` and is not presented
  as authoritative.
- Please do not reformat the JSON, reorder keys or change other locales in the
  same pull request.

## After your review

- We apply or merge the change, run the test suite and remove the language from
  `needs_review`.
- The entry is then treated as reviewed; the Arabic remains the reference.
- You are credited in the release notes, with your permission.

## Time and credit

Roughly 15–30 minutes per language; Somali has eight entries, so allow a little
more.

Questions about the wording, the sources or the process are welcome on this
issue. Thank you.

---

*The app is in beta; this queue is the remaining review debt for the Hisn
morning/evening set.*

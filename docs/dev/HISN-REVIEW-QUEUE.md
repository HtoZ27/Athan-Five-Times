# Native review queue — Hisn morning/evening

> Generated from `translation_meta.needs_review` in `assets/adhkar/{morning,evening}.json` on 2026-11-17, after commit `5fda5a6`.
> **17 entries / 8 items.** This is not a translation gap: all 51 morning/evening ids exist in all 16 non-Arabic locales.
> The entries below were composed or adapted by the assistant, so a native speaker must check them before they are treated as authoritative.

## How to sign off

1. Compare the translation with the Arabic and with the register of the published Hisn text.
2. If it is correct, remove that language from `translation_meta.needs_review[item]` in the JSON and from `NEEDS_REVIEW` in `tests/test_adhkar_repo.py`.
3. If it needs edits, update `translations[lang]` in the JSON and keep the entry flagged until it is re-checked.
4. Run `python3 -m pytest tests/test_adhkar_repo.py -q` after every change.

## Summary

| # | Item(s) | Languages | Why flagged |
|---|---|---|---|
| 1 | `m04` / `e08` | `ur`, `pa`, `ps`, `so` | Published text says نبي and orders Allah–Islam–Muhammad; adapted to رسولًا and the repo order. |
| 2 | `m05` | `ur`, `pa`, `ps`, `so` | Only the first half is published; the second half (سبحان الله العظيم) was appended. |
| 3 | `mor27` / `eve26` | `so` | Published Somali covers the short istighfar; the long form was expanded. |
| 4 | `e03` | `so` | Morning wording adapted to evening with the book's own substitution rule. |
| 5 | `eve16` | `so` | Morning wording adapted to evening; the previous text still used the morning verb. |
| 6 | `eve20` | `so` | Morning wording adapted to evening with the book's own substitution rule. |

## 1. `m04` / `e08` — رضيت بالله ربًا وبمحمد رسولًا وبالإسلام دينًا

**Items:** `morning:m04`, `evening:e08`  
**Flagged languages:** `ur`, `pa`, `ps`, `so` (8 entries)  
**Why flagged:** The published islambook text says **نبيا** and orders *Allah–Islam–Muhammad*; the repo Arabic says **رسولًا** and orders *Allah–Muhammad–Islam*. The translations were adapted to the repo wording. The existing Somali text also changed `nabinimo` → `rasuulnimo`, but it still keeps the narration wrapper (`qofkii yiraahda…`) and the opening quote; the Arabic item is the dhikr alone, so the reviewer should decide whether to trim it.  
**Source:** islambook.com `ur`/`pa`/`ps` → `/azkr/1` (m04) and `/azkr/2` (e08); Somali: hisnmuslim.com/i/so/1.

**Arabic**

> رَضِيتُ بِاللَّهِ رَبًّا وَبِمُحَمَّدٍ رَسُولًا وَبِالْإِسْلَامِ دِينًا

**Translations to review** (the same text applies to both ids)

- [ ] `ur` — میں اللہ کے رب ہونے، محمد صلی اللہ علیہ وسلم کے رسول ہونے اور اسلام کے دین ہونے پر راضی ہوں۔
- [ ] `pa` — ਮੈਂ ਅੱਲਾਹ ਨੂੰ ਰੱਬ, ਮੁਹੰਮਦ ਉੱਤੇ ਅੱਲਾਹ ਦੀ ਰਹਿਮਤ ਅਤੇ ਸਲਾਮਤੀ ਹੋਵੇ ਨੂੰ ਰਸੂਲ ਅਤੇ ਇਸਲਾਮ ਨੂੰ ਦੀਨ ਮੰਨ ਕੇ ਰਾਜ਼ੀ ਹਾਂ।
- [ ] `ps` — زه په الله د رب، په محمد ﷺ د رسول او په اسلام د دين په توګه راضي يم.
- [ ] `so` — qofkii yiraahda saddex mar subaxdii, saddex marna galabkii, waxaa balan ah in ilaahay raali galiyo maalinta qiyaamaha. “waxaan raali uga ahay ilaahay rabbinimo, islaamkana diinimo, muxammadna s.c.w rasuulnimo

## 2. `m05` — سبحان الله وبحمده، سبحان الله العظيم

**Items:** `morning:m05`  
**Flagged languages:** `ur`, `pa`, `ps`, `so` (4 entries)  
**Why flagged:** islambook (ur/pa/ps) and hisnmuslim (so) publish only the first half (**سبحان الله وبحمده**). The second half (**سبحان الله العظيم**) was appended by analogy in each language, in the same register.  
**Source:** islambook.com `ur`/`pa`/`ps` → `/azkr/1` (`zekr-223`); Somali: hisnmuslim.com/i/so/1.

**Arabic**

> سُبْحَانَ اللَّهِ وَبِحَمْدِهِ، سُبْحَانَ اللَّهِ الْعَظِيمِ

**Translation to review**

- [ ] `ur` — اللہ اپنی حمد کے ساتھ پاک ہے۔ اللہ بہت عظمت والا ہے۔
- [ ] `pa` — ਅੱਲਾਹ ਪਾਕ ਹੈ ਅਤੇ ਉਸੇ ਦੀ ਸਾਰੀ ਤਾਰੀਫ਼ ਹੈ। ਅੱਲਾਹ ਬਹੁਤ ਮਹਾਨ ਹੈ।
- [ ] `ps` — الله پاک دی او ستاينه يې کوم. الله لوی دی.
- [ ] `so` — Ilaahaybaa xumaan ka hufan, mahadna leh. Ilaahaybaa xumaan ka hufan, waa weyn yahay.

## 3. `mor27` / `eve26` — أستغفر الله العظيم الذي لا إله إلا هو الحي القيوم وأتوب إليه

**Items:** `morning:mor27`, `evening:eve26`  
**Flagged languages:** `so` (2 entries)  
**Why flagged:** The published Somali text covers the short istighfar (**أستغفر الله وأتوب إليه**). The repo Arabic uses the long form (**العظيم الذي لا إله إلا هو الحي القيوم**), so the Somali was expanded to match. The same text is used for the morning and evening ids.  
**Source:** hisnmuslim.com/i/so/1 (short istighfar), expanded for the repo's long form.

**Arabic**

> أسْتَغْفِرُ اللهَ العَظِيمَ الَّذِي لاَ إلَهَ إلاَّ هُوَ، الحَيُّ القَيُّومُ، وَأتُوبُ إلَيهِ.

**Translations to review** (the same text applies to both ids)

- [ ] `so` — Ilaahayga weyn ayaan dambi dhaaf weydiisanayaa, kaas oo aan Ilaah kale oo xaq lagu caabudo jirin isaga mooyee, waa nool yahay oo arrimaha oo dhan qabanayaa, una toobad keenayaa.

## 4. `e03` — أمسينا وأمسى الملك لله والحمد لله…

**Items:** `evening:e03`  
**Flagged languages:** `so` (1 entry)  
**Why flagged:** The published Somali source gives the morning wording. The evening form was derived with the substitution rule used by the book itself: `waan waabariisanay` → `Waan galabaysanay`, `wey waabariisatay` → `waxay galabaysatay`, `maalintan` → `habeenkan`.  
**Source:** hisnmuslim.com/i/so/1 (morning wording) + the book's morning→evening rule.

**Arabic**

> أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ وَالْحَمْدُ لِلَّهِ، لَا إِلَهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ وَهُوَ عَلَى كُلِّ شَيْءٍ قَدِيرٌ، رَبِّ أَسْأَلُكَ خَيْرَ مَا فِي هَذِهِ اللَّيْلَةِ وَخَيْرَ مَا بَعْدَهَا، وَأَعُوذُ بِكَ مِنْ شَرِّ مَا فِي هَذِهِ اللَّيْلَةِ وَشَرِّ مَا بَعْدَهَا، رَبِّ أَعُوذُ بِكَ مِنَ الْكَسَلِ وَسُوءِ الْكِبَرِ، رَبِّ أَعُوذُ بِكَ مِنْ عَذَابٍ فِي النَّارِ وَعَذَابٍ فِي الْقَبْرِ

**Translation to review**

- [ ] `so` — Waan galabaysanay, boqornimaduna waxay galabaysatay iyadoo u sugnaatay Ilaahay, mahad Ilaahay ayaa leh, Ilaah xaq lagu caabudaana ma jiro Ilaahay mooyee kaligii, cid wax la wadaagtana malaha, wuxuu leeyahay boqornimada, wuxuuna leeyahay mahadda, shay kastana wuu karaa, Rabbiyow waxaan ku weydiisanayaa (inaad i siiso) khayrka habeenkan iyo khayrka ka dambeeya, waxaan kaa magan galayaa sharka habeenkan iyo sharka ka dambeeya, Rabbiyow waxaan kaa magan galayaa caajiska, waxaana kaa magan galayaa gabow-xumi, Rabbiyow waxaan kaa magan galayaa cadaab naarta iyo cadaab qabriga.

## 5. `eve16` — أمسينا على فطرة الإسلام…

**Items:** `evening:eve16`  
**Flagged languages:** `so` (1 entry)  
**Why flagged:** Only the morning wording (**أصبحنا على فطرة الإسلام**) is published. The evening form was derived with the same rule. The text merged earlier still said `waxaan ku waa bariisanay` (morning); it was corrected to `Waxaan ku galabaysanay` in commit `5fda5a6` and remains flagged for review.  
**Source:** hisnmuslim.com/i/so/1 (morning wording) + the book's morning→evening rule.

**Arabic**

> أَمْسَيْنَا عَلَى فِطْرَةِ الإسْلاَمِ، وَعَلَى كَلِمَةِ الإِخْلاَصِ، وَعَلَى دِينِ نَبِيِّنَا مُحَمَّدٍ صَلَّى اللهُ عَلَيْهِ وَسَلَّمَ، وَعَلَى مِلَّةِ أَبِينَا إبْرَاهِيمَ حَنِيفاً مُسْلِماً وَمَا كَانَ مِنَ المُشْرِكِينَ.

**Translation to review**

- [ ] `so` — Waxaan ku galabaysanay fidrada(diinta) islaamka, iyo kalmada runta ah, iyo diinta nabigeena muxammad s.c.w iyo diinta aabaheen ibraahiim ee ahaa mid ka iishay diimaha(gaalada) oo dhan, muslimna ahaa, kamana mid ahayn mushrikiinta(gaalada).

## 6. `eve20` — أمسينا وأمسى الملك لله رب العالمين…

**Items:** `evening:eve20`  
**Flagged languages:** `so` (1 entry)  
**Why flagged:** The published Somali source gives the morning wording. The evening form was derived with the same substitution rule, including the gender agreement of `فتحها/نصرها/نورها/بركتها/هداها` → `fatxigiisa/gargaarkiisa/nuurkiisa/barakadiisa/hanuunkiisa` for the masculine *habeen* (night).  
**Source:** hisnmuslim.com/i/so/1 (morning wording) + the book's morning→evening rule.

**Arabic**

> أَمْسَيْنَا وَأَمْسَى الْمُلْكُ لِلَّهِ رَبِّ الْعَالَمِينَ، اللَّهُمَّ إِنِّي أَسْأَلُكَ خَيْرَ هَذِهِ اللَّيْلَةِ فَتْحَهَا وَنَصْرَهَا وَنُورَهَا وَبَرَكَتَهَا وَهُدَاهَا، وَأَعُوذُ بِكَ مِنْ شَرِّ مَا فِيهَا وَشَرِّ مَا بَعْدَهَا

**Translation to review**

- [ ] `so` — Waan galabaysanay, boqornimaduna waxay galabaysatay iyadoo u sugnaatay Ilaahaygii caalamiinta rabigooda ahaa, Allow waxaan ku weydiisanayaa khayrka habeenkan, fatxigiisa (furashadiisa), iyo gargaarkiisa, iyo nuurkiisa iyo barakadiisa iyo hanuunkiisa, waxaana kaa magan galayaa sharka ku sugan dhexdiisa iyo sharka ka dambeeyaba.

## After all entries are signed off

`translation_meta.needs_review` becomes `{}` in both files, `NEEDS_REVIEW` in the test becomes `{}`, and the Hisn batch has no outstanding review debt. Until then, the flags and this queue must stay in sync.

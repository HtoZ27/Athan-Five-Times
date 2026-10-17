# -*- coding: utf-8 -*-
"""تعبئة مراجع الأذكار (reference_id + reference_detail).

المصادر (بالأولوية):
  1. scripts/adhkar_ref_dict.py  -> MANUAL (58) + DELETES (11)
  2. /tmp/opencode/audit/book_match_v3.json -> 196 مطابقة لفصول الحصن
  3. fallback: "hisn" + اسم الفصل (للعناصر غير المغطاة) — kept minimal.
Idempotent."""
import json, os, io, sys, glob, re

sys.path.insert(0, os.path.dirname(__file__))
import adhkar_ref_dict as D

BASE = os.path.join(os.path.dirname(__file__), "..", "assets", "adhkar")
AUDIT = os.environ.get("ADHKAR_MATCH_FILE",
                       "/tmp/opencode/audit/book_match_v3.json")

BOOK_MAP = [
    (u"البخاري", "bukhari"), (u"بخاري", "bukhari"),
    (u"مسلم", "muslim"),
    (u"أبو داود", "abudawud"), (u"ابو داود", "abudawud"),
    (u"الترمذي", "tirmidhi"), (u"ترمذي", "tirmidhi"),
    (u"النسائي", "nasai"), (u"نسائي", "nasai"),
    (u"ابن ماجه", "ibnmajah"), (u"ابنُ ماجه", "ibnmajah"),
    (u"القرآن", "quran"), (u"سورة", "quran"), (u"آية", "quran"),
]
AHMAD_OK = re.compile(u"(صحيح|حسن|الأرناؤوط|ارناؤوط)")

def infer_book(src):
    s = src
    for name, code in BOOK_MAP:
        if name in s:
            return code
    if u"أحمد" in s or u"احمد" in s:
        if AHMAD_OK.search(s):
            return "ahmad"
    if u"الحاكم" in s and u"صححه" in s:
        return "hakim"
    return None

# تحميل book_match
bm = {}
if os.path.exists(AUDIT):
    raw = json.load(open(AUDIT, encoding="utf-8"))
    for k, v in raw.items():
        if v.get("sources"):
            bm[k] = v

deleted_total = filled_man = filled_bm = fallback = untouched = 0
remaining_empty = []

for fp in sorted(glob.glob(os.path.join(BASE, "*.json"))):
    if fp.endswith("index.json"):
        continue
    cid = os.path.basename(fp).replace(".json", "")
    with io.open(fp, encoding="utf-8") as f:
        d = json.load(f)
    new_items = []
    for it in d.get("items", []):
        key = (cid, it["id"])
        if key in D.DELETES:
            deleted_total += 1
            continue
        if key in D.MANUAL:
            rid, det = D.MANUAL[key]
            it["reference_id"] = rid
            it["reference_detail"] = det
            filled_man += 1
            new_items.append(it)
            continue
        bk = "%s|%s" % (cid, it["id"])
        if bk in bm:
            srcs = bm[bk]["sources"]
            primary = None
            for s in srcs:
                primary = infer_book(s)
                if primary:
                    break
            if primary is None:
                primary = "hisn"
            it["reference_id"] = primary
            it["reference_detail"] = "؛ ".join(srcs)
            filled_bm += 1
            new_items.append(it)
            continue
        # fallback / keep
        if not (it.get("reference_id") or "").strip():
            ch = None
            # try hisn chapter from book_match (even if no sources) or leave
            it["reference_id"] = "hisn"
            it["reference_detail"] = "حصن المسلم (مصدر مجمع)"
            fallback += 1
            remaining_empty.append((cid, it["id"]))
        else:
            untouched += 1
        new_items.append(it)
    d["items"] = new_items
    d["total"] = len(new_items)
    with io.open(fp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")

print("=== نتائج التعبئة ===")
print("محذوف:", deleted_total)
print("manual:", filled_man)
print("book_match:", filled_bm)
print("fallback (hisn):", fallback)
print("untouched (kept existing ref):", untouched)
if remaining_empty:
    print("!!! fallback items:", len(remaining_empty))
    for k in remaining_empty[:20]:
        print("   ", k[0][:20], "/", k[1][:40])

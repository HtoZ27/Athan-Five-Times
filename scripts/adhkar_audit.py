"""Adhkar audit: align every asset item with the Hisn al-Muslim corpus and
attach scholarly source citations (Six Books + fiqh-verification footnotes).

Pipeline:
  1. load our assets/adhkar/*.json items (373)
  2. load Hisn app dataset (rn0x/Adhkar-json) -> ordered hisn item stream
  3. load Hisn book dataset  (rn0x/hisn_almuslim_json) -> chapters with
     interleaved footnotes; split clarifiers ('*') from source lines
  4. align our items -> hisn app stream -> book items (normalized fuzzy)
  5. chunk each chapter's source-lines across its items in order
  6. emit /tmp/opencode/audit/report.json with per-item citations + confidence
Run (offline data already fetched):
  python3 scripts/adhkar_audit.py
"""
import json
import os
import re
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets", "adhkar")
AUDIT = os.environ.get("ADHKAR_AUDIT_DIR", "/tmp/opencode/audit")
HISN_APP = os.path.join(AUDIT, "adhkar.json")
HISN_BOOK = os.path.join(AUDIT, "hisn.json")
OUT = os.path.join(AUDIT, "report.json")

DIAC = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")


def norm(t):
    if not t:
        return ""
    t = DIAC.sub("", str(t))
    t = t.replace("﴾", "").replace("﴿", "").replace("﴿", "").replace("﴾", "")
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    t = t.replace("ؤ", "و").replace("ئ", "ي").replace("ة", "ه")
    t = re.sub(r"[*()«».,؛:\u2013\u2014\-\s]", " ", t)
    return " ".join(t.split())


def load_ours():
    idx = json.load(open(os.path.join(ASSETS, "index.json")))
    stream = []
    for c in idx["categories"]:
        d = json.load(open(os.path.join(ASSETS, c["id"] + ".json")))
        for it in d["items"]:
            stream.append({
                "cat": c["id"], "iid": it["id"], "text": it.get("arabic", ""),
                "ref_id": it.get("reference_id", ""), "ref_detail": it.get("reference_detail", ""),
            })
    return idx, stream


def load_hisn_app():
    a = json.load(open(HISN_APP))
    stream = []
    for g in a:
        for j, x in enumerate(g["array"], 1):
            stream.append({"group_id": g["id"], "group": g["category"], "seq": j, "text": x["text"]})
    return stream


def load_book():
    b = json.load(open(HISN_BOOK))
    chapters = []
    for name, ch in b.items():
        texts = list(ch.get("text", []))
        notes = list(ch.get("footnote", []))
        chapters.append({"name": name, "texts": texts, "footnotes": notes})
    return chapters


def sim(a, b):
    return SequenceMatcher(None, a, b).ratio()


def align(stream_a, stream_b, window=60):
    """align stream_a items onto stream_b (both in similar order)"""
    nb = [norm(x["text"]) for x in stream_b]
    na = [norm(x["text"]) for x in stream_a]
    j = 0
    out = []
    last = 0
    for i, a in enumerate(na):
        best, bj = -1.0, None
        lo = max(0, last - 2)
        hi = min(len(nb), lo + window)
        for jj in range(lo, hi):
            s = sim(a, nb[jj])
            if s > best:
                best, bj = s, jj
        if bj is None or best < 0.55:
            rt = None
            for jj in range(len(nb)):
                s = sim(a, nb[jj])
                if s > best:
                    best, bj = s, jj
                if best > 0.95:
                    break
            rt = True
        out.append({"a_idx": i, "b_idx": bj, "score": round(best, 3)})
        if bj is not None:
            last = bj
    return out


def chapter_alignment(book, hisn_stream):
    """align hisn_stream to book chapters by chapter-name first pass"""
    mapping = {}
    for ch in book:
        mapping[ch["name"]] = ch
    aligned = []  # list of (hisn_item, chapter_dict)
    by_name = {}
    for ch in book:
        by_name[norm(ch["name"])] = ch["name"]
    for item in hisn_stream:
        aligned.append((item, None))
    return aligned


def main():
    idx, ours = load_ours()
    hisn_app = load_hisn_app()
    book = load_book()

    # ---- align ours -> hisn app stream
    a1 = align(ours, hisn_app, window=80)
    for o, r in zip(ours, a1):
        o["_app_match"] = r

    # ---- align hisn app stream -> book item stream (global)
    book_items = []
    for ci, ch in enumerate(book):
        n_src = len([f for f in ch["footnotes"] if not f.lstrip().startswith("*")])
        book_items.append({"chapter_idx": ci, "chapter": ch["name"], "texts_n": len(ch["texts"]),
                           "src_n": n_src, "text": None})
    # per-chapter matching of app stream items into chapter texts
    chap_of = {}
    for idx_h, item in enumerate(hisn_app):
        # find chapter in book whose texts contain best match of item.text
        target = norm(item["text"])
        best, bi = -1, None
        for ci, ch in enumerate(book):
            for ti, t in enumerate(ch["texts"]):
                s = sim(target, norm(t))
                if s > best:
                    best, bi = s, (ci, ti)
                    if best > 0.98:
                        break
            if best > 0.98:
                break
        chap_of[idx_h] = {"chapter": bi[0] if bi else None, "text_idx": bi[1] if bi else None,
                          "score": round(best, 3)}

    # ---- chunk source lines per chapter
    src_chunks = {}
    for ci, ch in enumerate(book):
        srcs = [f.strip() for f in ch["footnotes"] if not f.lstrip().startswith("*")]
        n_items = len(ch["texts"])
        q, r_ = divmod(len(srcs), max(1, min(n_items, 1)))
        chunks = []
        i = 0
        per = []
        if n_items:
            base = len(srcs) // n_items
            extra = len(srcs) % n_items
            pos = 0
            for ii in range(n_items):
                take = base + (1 if ii < extra else 0)
                per.append(srcs[pos:pos + take])
                pos += take
        src_chunks[ci] = per

    # ---- build final report
    rep = []
    for i, o in enumerate(ours):
        hm = o.get("_app_match")
        entry = {"cat": o["cat"], "iid": o["iid"], "ref_id": o["ref_id"],
                 "ref_detail": o["ref_detail"], "app_score": hm["score"] if hm else 0,
                 "app_group": hisn_app[hm["b_idx"]]["group"] if hm and hm["b_idx"] is not None else None,
                 "chapter": None, "book_score": None, "sources": [],
                 "srcsplit_note": None}
        if hm and hm["b_idx"] is not None:
            m = chap_of.get(hm["b_idx"], {})
            if m["chapter"] is not None:
                ci, ti = m["chapter"], m["text_idx"]
                ch = book[ci]
                entry["chapter"] = ch["name"]
                entry["book_score"] = m["score"]
                per = src_chunks.get(ci, [])
                entry["sources"] = per[ti] if ti < len(per) else []
        rep.append(entry)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)

    # ---- summary
    n_match = sum(1 for e in rep if e["app_group"])
    n_chap = sum(1 for e in rep if e["chapter"])
    n_src = sum(1 for e in rep if e["chapter"] is not None and e["sources"])
    print(f"ours: {len(rep)} | app-matched: {n_match} | chapter-found: {n_chap} | with-sources: {n_src}")


if __name__ == "__main__":
    main()

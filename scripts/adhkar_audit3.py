"""Adhkar audit pass 2: direct-book matching for items the app-dataset missed,
plus consolidated type classification + deletions list."""
import json
import os
import re
import unicodedata
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets", "adhkar")
AUDIT = os.environ.get("ADHKAR_AUDIT_DIR", "/tmp/opencode/audit")
OUT = os.path.join(AUDIT, "report3.json")
DIAC = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED]")


def norm(t):
    if not t:
        return ""
    t = unicodedata.normalize("NFKC", str(t))
    t = DIAC.sub("", t)
    for a, b in [("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ؤ", "و"), ("ئ", "ي"),
                 ("ة", "ه"), ("ى", "ي"), ("ٱ", "ا"), ("ۥ", ""), ("ٓ", ""), ("ٰ", "")]:
        t = t.replace(a, b)
    t = re.sub(r"[^\u0620-\u06FF\s]", " ", t)
    return " ".join(t.split())


def words(t):
    return set(norm(t).split())


def load_ours():
    idx = json.load(open(os.path.join(ASSETS, "index.json")))
    stream = []
    for c in idx["categories"]:
        d = json.load(open(os.path.join(ASSETS, c["id"] + ".json")))
        for it in d["items"]:
            stream.append({"cat": c["id"], "iid": it["id"], "text": it.get("arabic", ""),
                           "ref_id": it.get("reference_id", ""), "ref_detail": it.get("reference_detail", "")})
    return stream


def load_book():
    b = json.load(open(os.path.join(AUDIT, "hisn.json")))
    chapters = []
    for name, ch in b.items():
        chapters.append({"name": name, "texts": list(ch.get("text", [])),
                         "footnotes": list(ch.get("footnote", []))})
    return chapters


def chunk_sources(ch):
    srcs = [f.strip() for f in ch["footnotes"] if not f.lstrip().startswith("*")]
    n = len(ch["texts"])
    if not n or not srcs:
        return []
    per, base, extra, pos = [], len(srcs) // n, len(srcs) % n, 0
    for i in range(n):
        take = base + (1 if i < extra else 0)
        per.append((srcs[pos:pos + take], (take,)))
        pos += take
    return per


def main():
    ours = load_ours()
    book = load_book()

    rep2 = json.load(open(os.path.join(AUDIT, "report2.json")))
    byid = {(e["cat"], e["iid"]): e for e in rep2}

    flatbook = []
    for ci, ch in enumerate(book):
        per = chunk_sources(ch)
        for ti, t in enumerate(ch["texts"]):
            flatbook.append({"ci": ci, "ti": ti, "chapter": ch["name"], "wnorm": norm(t),
                             "sources": per[ti][0] if ti < len(per) else []})

    direct, manual = {}, {}
    for o in ours:
        e = byid.get((o["cat"], o["iid"]))
        if e and e["gname"]:
            continue  # already sourced via app alignment
        tn, ws = norm(o["text"]), words(o["text"])
        best, bj = -1.0, None
        for j, fl in enumerate(flatbook):
            lr = len(tn) / max(1, len(fl["wnorm"]))
            if lr < 0.4 or lr > 2.5:
                continue
            if len(fl["wnorm"]) < 12:
                continue
            if len(ws & set(fl["wnorm"].split())) < 2:
                continue
            s = SequenceMatcher(None, tn, fl["wnorm"]).ratio()
            if s > best:
                best, bj = s, j
        if bj is not None and best >= 0.6:
            fl = flatbook[bj]
            direct[(o["cat"], o["iid"])] = {"chapter": fl["chapter"], "score": round(best, 3),
                                            "sources": fl["sources"], "ref": o["ref_id"]}
        else:
            manual[(o["cat"], o["iid"])] = {"score": round(best, 3) if bj else None,
                                            "chapter": flatbook[bj]["chapter"] if bj else None,
                                            "sources": flatbook[bj]["sources"] if bj else [],
                                            "ref": o["ref_id"]}

    out = {"direct matched": [{"cat": c, "iid": i, **v} for (c, i), v in direct.items()],
           "manual candidates": [{"cat": c, "iid": i, **v} for (c, i), v in manual.items()]}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("direct-book matched:", len(direct), "| manual:", len(manual))
    for m in out["direct matched"]:
        print("  DB:", f"{m['cat'][:14]:14s}", f"{m['iid'][:38]:38s}", m["chapter"][:26], m["sources"][:1])
    print()
    for m in out["manual candidates"]:
        print("  MAN:", f"{m['cat'][:14]:14s}", f"{m['iid'][:44]:44s}", f"ref={m['ref']:9s}",
              f"best={m['score']}", (m["chapter"] or "")[:22])


if __name__ == "__main__":
    main()

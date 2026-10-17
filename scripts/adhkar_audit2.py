"""Adhkar audit v2: precise per-item source citations.

Steps:
  A. build app-group -> book-chapter explicit name map
  B. global best-match of our 373 items onto hisn app stream (prefiltered)
  C. map matched app item -> chapter -> best text index -> source chunk
  D. report + console summary of items needing manual attention
"""
import json
import os
import re
import unicodedata
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets", "adhkar")
AUDIT = os.environ.get("ADHKAR_AUDIT_DIR", "/tmp/opencode/audit")
OUT = os.path.join(AUDIT, "report2.json")

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


def load_ours():
    idx = json.load(open(os.path.join(ASSETS, "index.json")))
    stream = []
    for c in idx["categories"]:
        d = json.load(open(os.path.join(ASSETS, c["id"] + ".json")))
        for it in d["items"]:
            stream.append({"cat": c["id"], "iid": it["id"], "text": it.get("arabic", ""),
                           "ref_id": it.get("reference_id", ""), "ref_detail": it.get("reference_detail", "")})
    return stream


def load_app():
    a = json.load(open(os.path.join(AUDIT, "adhkar.json")))
    g = []
    for gi, x in enumerate(a):
        grp = {"gid": gi, "name": x["category"], "items": [], "n": []}
        for j, it in enumerate(x["array"]):
            grp["items"].append(it["text"])
            grp["n"].append(it.get("count"))
        g.append(grp)
    return g


def load_book():
    b = json.load(open(os.path.join(AUDIT, "hisn.json")))
    chapters = []
    for name, ch in b.items():
        chapters.append({"name": name, "texts": list(ch.get("text", [])), "footnotes": list(ch.get("footnote", []))})
    return chapters


def sim(a, b):
    return SequenceMatcher(None, a, b).ratio()


def words(t):
    return set(norm(t).split())


def main():
    ours = load_ours()
    app = load_app()
    book = load_book()

    # ---- chapter name map: app group name -> book chapter name
    nb = {norm(c["name"]): c["name"] for c in book}
    g2c, unresolved = {}, []
    for grp in app:
        n = norm(grp["name"])
        cands = [(sim(n, k), k) for k in nb]
        s, k = max(cands, key=lambda x: x[0])
        if s >= 0.62:
            g2c[grp["gid"]] = nb[k]
        else:
            unresolved.append(grp["gid"])
    print("unresolved group->chapter:", [app[i]["name"] for i in unresolved])

    # ---- global best match ours -> app items
    app_flat = []
    for grp in app:
        for j, t in enumerate(grp["items"]):
            app_flat.append({"gid": grp["gid"], "gname": grp["name"], "idx": j, "text": t,
                             "wnorm": norm(t), "wset": words(t)})

    matches = {}
    for o in ours:
        t = o["text"]
        tn, ws = norm(t), words(t)
        best, bj = -1.0, None
        for j, aitem in enumerate(app_flat):
            rr = len(tn) / max(1, len(aitem["wnorm"]))
            if rr < 0.45 or rr > 2.2:
                continue
            if len(ws & aitem["wset"]) < 2:
                continue
            s = sim(tn, aitem["wnorm"])
            if s > best:
                best, bj = s, j
        matches[o["iid"]] = {"score": round(best, 3), "ai": bj}

    # ---- chapter text index + sources
    rep = []
    for o in ours:
        e = {"cat": o["cat"], "iid": o["iid"], "text": o["text"][:60],
             "old_ref": f"{o['ref_id']} {o['ref_detail']}".strip(),
             "app_score": matches[o["iid"]]["score"],
             "gname": None, "chapter": None, "coc": None, "sources": [],
             "chapter_texts_left": None}
        m = matches.get(o["iid"])
        if m and m["score"] >= 0.55 and m["ai"] is not None:
            fl = app_flat[m["ai"]]
            e["gname"] = fl["gname"]
            chname = g2c.get(fl["gid"])
            ch = next((c for c in book if c["name"] == chname), None)
            if ch:
                e["chapter"] = chname
                tn, ws = norm(o["text"]), words(o["text"])
                best, bi = -1.0, None
                for ti, t in enumerate(ch["texts"]):
                    s = sim(tn, norm(t))
                    if s > best:
                        best, bi = s, ti
                e["coc"] = round(best, 3)
                e["chapter_texts_left"] = len(ch["texts"])
                srcs = [f.strip() for f in ch["footnotes"] if not f.lstrip().startswith("*")]
                n_items = len(ch["texts"])
                chunks = []
                if n_items and srcs:
                    per = []
                    base = len(srcs) // n_items
                    extra = len(srcs) % n_items
                    pos = 0
                    for ii in range(n_items):
                        take = base + (1 if ii < extra else 0)
                        per.append(srcs[pos:pos + take] if take else [])
                        pos += take
                    chunks = per
                e["sources"] = chunks[bi] if bi < len(chunks) else []
        rep.append(e)

    json.dump(rep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    n_g = sum(1 for e in rep if e["gname"])
    n_c = sum(1 for e in rep if e["chapter"])
    n_s = sum(1 for e in rep if e["chapter"] and e["sources"])
    low = [e for e in rep if not e["gname"]]
    lowch = [e for e in rep if e["gname"] and not e["chapter"]]
    print(f"ours {len(rep)} | app-gname {n_g} | chapter {n_c} | sourced {n_s}")
    print("no app match:", len(low), "| gname ok but chapter missing:", len(lowch))
    for e in low[:40]:
        print("  NOAPP:", e["cat"], e["iid"], "|", e["old_ref"], "|", e["text"])


if __name__ == "__main__":
    main()

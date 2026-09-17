#!/usr/bin/env python3
"""Build the variant-to-canonical map a register search folds spellings with.

WHY. FilterTable has taken a `fold` map since the Blazevic register moved onto
it, and until today five wrapper components dropped the prop, so one page in the
whole estate used it. Measured on the Booyzen register that is not a nicety: the
surname is written six ways across 4,244 tokens, and a reader who types the
canonical spelling reaches 3,504 of them and never learns the other 740 exist.
D'Arcy is worse - its commonest spelling is 46% of its entries.

WHAT IT DOES NOT DO. Folding is a SEARCH rule, not an identity rule. It widens
what a query matches; it never merges two records, never joins two people and
never touches a chart. This estate does not merge on a name and this does not
change that - it is the opposite, a way of SEEING the other spellings rather
than quietly missing them.

HOW THE CLUSTERS ARE FORMED. Every surname token in the archive's own corpus is
reduced by the orthographic rules that actually vary in these records - ij/y,
s/z, doubled letters, diacritics - and tokens reducing to the same key cluster
together. THE CANONICAL FORM IS THE ARCHIVE'S OWN, taken from people.json, never
the commonest spelling: the Master's office spelled this family BOOYZEN and the
parish spelled it BOOYSEN, and which of those an archive answers to is its
decision, not a majority vote.

EVERY CLUSTER IS PRINTED. A fold that quietly joined two families would be the
worst bug this kit could ship, so the tool is loud and the output is meant to be
read before it is committed.

  python3 namefold.py --root site            # writes src/data/namefold.json
  python3 namefold.py --root site --dry      # print the clusters, write nothing
"""
import io, os, re, sys, json, glob, argparse, unicodedata
from collections import Counter, defaultdict


def key(w):
    """The spelling rules that vary in these registers, and no others."""
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    w = w.replace("ÿ", "y").replace("ij", "y").replace("ck", "k")
    w = w.replace("z", "s")                       # Booyzen / Booysen
    w = w.replace("y", "i")                       # Booysen / Booisen
    return w


# THERE IS NO DOUBLED-LETTER RULE, and there was one for about ten minutes.
# Collapsing repeats reduces Roos and Ross to the same key, and Roos and Ross are
# two different families in this archive - the first Dutch, the second Scottish,
# 2,030 tokens against 563. It would also have caught Kolbee for Kolbe and
# Grobbelaar for Grobelaar, which is twenty-odd tokens between them. Twenty
# tokens is not worth one wrong family. FOLDING IS ALLOWED TO MISS; IT IS NOT
# ALLOWED TO JOIN.
ROMAN = re.compile(r"^[IVXLC]+$")


def corpus(data):
    """Every word the archive's own records actually contain, with counts."""
    c = Counter()
    for p in glob.glob(os.path.join(data, "*.json")):
        try:
            txt = io.open(p, encoding="utf-8").read()
        except Exception:
            continue
        for w in re.findall(r"\b[A-Z][A-Za-zÀ-ſ']{3,}\b", txt):
            if not ROMAN.match(w):
                c[w] += 1
    return c


def canon_surnames(data):
    """The names this archive answers to, from its own people file."""
    out = []
    for f in ("people.json", "dossiers.json"):
        p = os.path.join(data, f)
        if not os.path.exists(p):
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        rows = d.get("people") if isinstance(d, dict) else d
        if isinstance(rows, dict):
            rows = list(rows.values())
        for r in rows or []:
            n = (r.get("n") or "").strip()
            if n:
                out.append(n.split()[-1].strip("“”\"'"))
    return [w for w, _ in Counter(out).most_common()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="site")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--min", type=int, default=2,
                    help="ignore a variant seen fewer times than this")
    a = ap.parse_args()
    data = os.path.join(a.root, "src", "data")
    if not os.path.isdir(data):
        print("  namefold: no %s" % data); return 1

    words = corpus(data)
    canon = canon_surnames(data)
    if not canon:
        print("  namefold: no people file - nothing to anchor a cluster to"); return 1

    # only cluster around names this archive actually answers to
    anchors = {}
    for c in canon:
        anchors.setdefault(key(c), c)

    # A cluster the archive has looked at and REJECTED stays rejected. The place
    # to say "these two never fold" is a file somebody can read, not a rule.
    denyp = os.path.join(data, "namefold-deny.json")
    deny = set()
    if os.path.exists(denyp):
        deny = {w.lower() for w in
                json.load(io.open(denyp, encoding="utf-8")).get("never", [])}

    groups = defaultdict(Counter)
    for w, n in words.items():
        if len(key(w)) < 4 or w.lower() in deny:
            continue
        k = key(w)
        if k in anchors:
            groups[k][w] += n

    fold, shown = {}, 0
    print("  clusters, anchored on the archive's own spelling:")
    for k, forms in sorted(groups.items(), key=lambda kv: -sum(kv[1].values())):
        c = anchors[k]
        others = {w: n for w, n in forms.items()
                  if w.lower() != c.lower() and n >= a.min}
        if not others:
            continue
        shown += 1
        tot = sum(forms.values())
        reach = sum(n for w, n in forms.items() if c.lower() in w.lower())
        print("    %-16s %5d token(s) — typing %r reaches %d (%.0f%%)"
              % (c, tot, c, reach, 100.0 * reach / tot))
        for w, n in sorted(others.items(), key=lambda x: -x[1]):
            mark = " " if c.lower() in w.lower() else "+"
            print("      %s %-18s %5d" % (mark, w, n))
            fold[w.lower()] = c.lower()
        fold[c.lower()] = c.lower()

    extra = os.path.join(data, "namefold-extra.json")
    if os.path.exists(extra):
        e = json.load(io.open(extra, encoding="utf-8"))
        pairs = e.get("fold", e) if isinstance(e, dict) else {}
        for v, c in pairs.items():
            fold[v.lower()] = c.lower()
        print("  + %d pair(s) from namefold-extra.json (the archive's own, "
              "written not derived)" % len(pairs))

    print("  %d cluster(s), %d form(s) folded" % (shown, len(fold)))
    if a.dry:
        print("  --dry: nothing written"); return 0
    out = os.path.join(data, "namefold.json")
    json.dump({"note": "Variant → canonical, for SEARCH only. Built by "
                       "kit/tools/namefold.py; run it again rather than editing "
                       "it. Folding widens what a query matches and never merges "
                       "a record with another.",
               "fold": dict(sorted(fold.items()))},
              io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("  → %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

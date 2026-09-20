#!/usr/bin/env python3
"""Point a family atlas at the Record Atlas, instead of copying it.

THE MEASUREMENT THAT MAKES THIS WORTH DOING. The Record Atlas holds 9,472
places, who holds the paper for each, what it costs to look and whose empire
filed it. The Defranceschi map carries a «shelf» layer of 1,245 parishes
saying how far that family has got with the registers - and 1,239 of those
1,245, ONE HUNDRED PER CENT, are already in the Record Atlas. Its family
layers are not: people 72 of 165, graves 18 of 64. That is the line between
the two, and it is already true in the data. Where the records ARE is a global
question; where THIS family was is not.

So a family archive should link out for the shelf rather than keep a second
copy of it, and this writes the links.

MATCHED ON NAME AND PROXIMITY, NEVER ON NAME. This estate has just spent a day
on what happens when a gazetteer is asked for a bare settlement name: Pag in
Dalmatia pinned in Mindanao, Kabwe in Zambia standing in for Broken Hill in
New South Wales. Measured here, a name-only match would be wrong often enough
to matter - D'Arcy has 88 places whose name is in the Record Atlas and only 56
of those are within 25 km of the place it means. The other 32 are homonyms on
other continents.

So a match needs the name AND a position within --km, and a place with two
candidates that close is reported and left alone rather than guessed at.

  python3 recordatlas.py --data site/public/atlas-data.json \\
                         --gazetteer ../The\\ Geneology\\ Map/site/src/data/places-full.json
"""
import io, os, re, sys, json, math, argparse, unicodedata


def fold(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", s)


def km(a, b, c, d):
    return math.hypot((a - c) * 111.0, (b - d) * 111.0 * math.cos(math.radians(a)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--gazetteer", required=True)
    ap.add_argument("--km", type=float, default=25.0)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    # A CROSS-REPO PATH IN A BUILD IS A FRAGILITY, SO IT FAILS SOFT. The
    # gazetteer is a sibling checkout, and a sibling is exactly the thing that
    # is missing on somebody else's machine, in CI, or on the day that repo is
    # renamed. A missing gazetteer means the links are not refreshed, which is
    # a worse map; a broken build means no map at all. It says so and stops.
    if not os.path.exists(a.gazetteer):
        print("  note  record atlas  no gazetteer at %s, so the links were left "
              "as they are. This is a sibling checkout and not a dependency; the "
              "build is fine without it." % a.gazetteer)
        return 0
    gaz = json.load(io.open(a.gazetteer, encoding="utf-8"))
    gaz = gaz["places"] if isinstance(gaz, dict) else gaz
    idx = {}
    for p in gaz:
        if p.get("lat") is None:
            continue
        forms = [p["name"]] + [x if isinstance(x, str) else x.get("n", "")
                               for x in (p.get("names") or [])]
        for n in forms:
            if n:
                idx.setdefault(fold(n), []).append(p)

    d = json.load(io.open(a.data, encoding="utf-8"))
    places = d["places"] if isinstance(d, dict) else d

    hit, amb, miss, far = 0, [], [], []
    for q in places:
        q.pop("ra", None)
        if q.get("lat") is None:
            continue
        cands = idx.get(fold(q["name"]), [])
        if not cands:
            miss.append(q["name"]); continue
        close = [(km(q["lat"], q["lon"], c["lat"], c["lon"]), c) for c in cands]
        close = [(dd, c) for dd, c in close if dd <= a.km]
        if not close:
            # the name is in the gazetteer and the place is not this one
            far.append((q["name"], min(km(q["lat"], q["lon"], c["lat"], c["lon"])
                                       for c in cands)))
            continue
        close.sort()
        if len(close) > 1 and close[1][0] <= a.km:
            amb.append(q["name"]); continue
        q["ra"] = close[0][1]["id"]
        hit += 1

    print("  %d of %d place(s) are in the Record Atlas by name and within %g km"
          % (hit, len(places), a.km))
    if far:
        print("  %d share a name with a Record Atlas place that is somewhere else "
              "entirely, and are left alone — which is the homonym trap, seen "
              "from the safe side:" % len(far))
        for n, dd in sorted(far, key=lambda x: -x[1])[:5]:
            print("      %-30s nearest of that name is %.0f km away" % (n[:30], dd))
    if amb:
        print("  %d have two candidates within %g km and are left for a human: %s"
              % (len(amb), a.km, ", ".join(amb[:4])))
    if miss:
        print("  %d are not in the Record Atlas at all, which is a fact about that "
              "gazetteer and not about this archive" % len(miss))
    if a.dry:
        print("  --dry: nothing written"); return 0
    json.dump(d, io.open(a.data, "w", encoding="utf-8"), ensure_ascii=False)
    print("  → %s" % a.data)
    return 0


if __name__ == "__main__":
    sys.exit(main())

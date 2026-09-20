#!/usr/bin/env python3
"""Split one atlas file into an index the map draws and a file per place.

WHY. The Atlas fetched a single JSON holding every place and everything known
about each of them, and drew markers from it. That is right up to a few hundred
places and wrong after: the Defranceschi map is 2,556 KB, of which the markers
need 191 KB. 93% of what every visitor downloads before the first dot appears
is panel text for places they will never click.

The Record Atlas solved this first - "the index carries only what a marker
needs to be drawn and found, everything else arrives per place, on click" - and
it is the reason that map can hold 9,472 places. This is the same split, for
any archive on the shared component.

WHAT STAYS IN THE INDEX. Whatever a marker needs to be placed, sized, coloured
and found: name, lat, lon, cat or cats, n or ns, also, order, slug. Everything
else - the events, the films, the people, the prose - goes to its own file and
is fetched when somebody asks.

  python3 splitatlas.py --in site/public/map-data.json \\
                        --index site/public/map-index.json \\
                        --out site/public/map/p

Then pass detailBase="/map/p" to the Atlas beside the new dataUrl. Run it in
the build, after whatever writes the atlas file: the split is derived and must
never be edited by hand.
"""
import io, os, re, sys, json, shutil, argparse, unicodedata

KEEP = ["name", "lat", "lon", "cat", "cats", "n", "ns", "also", "order", "slug", "href"]


def slug(s):
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()[:80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--index", required=True)
    ap.add_argument("--out", required=True, help="directory for the per-place files")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    d = json.load(io.open(a.src, encoding="utf-8"))
    places = d["places"] if isinstance(d, dict) else d
    if not places:
        print("  splitatlas: no places in %s" % a.src); return 1

    index, details, clash = [], {}, []
    for p in places:
        key = p.get("slug") or p["name"]
        if key in details:
            # two places cannot share a file
            clash.append(key)
        row = {k: p[k] for k in KEEP if k in p}
        rest = {k: v for k, v in p.items() if k not in KEEP}
        index.append(row)
        details[key] = rest

    if clash:
        print("  splitatlas: %d place(s) share a key and would overwrite each "
              "other's file - give them a slug: %s" % (len(clash), ", ".join(clash[:5])))
        return 1

    head = {k: v for k, v in (d.items() if isinstance(d, dict) else [])
            if k != "places"}
    head["places"] = index
    head["split"] = ("The index only. Each place's detail is a file of its own "
                     "under the atlas's detailBase, fetched when a reader clicks "
                     "it. Built by kit/tools/splitatlas.py - do not edit either "
                     "side by hand.")

    full = len(json.dumps(d, ensure_ascii=False).encode())
    small = len(json.dumps(head, ensure_ascii=False).encode())
    big = max((len(json.dumps(v, ensure_ascii=False).encode()) for v in details.values()),
              default=0)
    print("  %d place(s): index %d KB, was %d KB - %.0f%% less before the first "
          "marker. Largest place file %.1f KB."
          % (len(places), small // 1024, full // 1024,
             100 * (1 - small / full) if full else 0, big / 1024))
    if a.dry:
        print("  --dry: nothing written"); return 0

    json.dump(head, io.open(a.index, "w", encoding="utf-8"), ensure_ascii=False)
    if os.path.isdir(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out, exist_ok=True)
    for k, v in details.items():
        json.dump(v, io.open(os.path.join(a.out, k + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False)
    print("  → %s and %d file(s) in %s" % (a.index, len(details), a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

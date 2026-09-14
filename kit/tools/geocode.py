#!/usr/bin/env python3
"""Put a coordinate on a place name, and say how sure it is.

Five of the seven archives list places and geocode none of them, so no map can
be drawn on any of them. This resolves a name against OpenStreetMap's
Nominatim and writes the answer into a shared cache, so the estate asks for
any given place exactly once however many archives hold it.

Three things it is careful about, each learnt from a wrong answer:

  * The first hit is not the best hit. "Sandgate, Queensland" returns a RAILWAY
    STATION above the suburb. Results are ranked by whether they are a
    populated place or an administrative boundary before importance is looked
    at at all.

  * A place is often recorded with detail Nominatim cannot match — a street, a
    farm, a church, a cemetery. If the whole string fails, the leading segment
    is dropped and the rest retried, so "German Savoy Church, Strand, London"
    can still land on the Strand.

  * A coordinate is a claim like any other. Every answer records what was asked,
    what came back, and whether the match was `exact` (a populated place or
    boundary whose name contains the town asked for) or `approx` (anything
    else, including a fallback to a shorter string). Nothing here is allowed to
    look as certain as a register entry.

Usage policy: Nominatim asks for at most one request a second and a real
User-Agent. Both are honoured; the cache means a re-run costs nothing.
"""
import json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

UA = ("TheArchiveKit-geocoder/1.0 (family-history static sites; "
      "contact david.defranceski@gmail.com)")
ENDPOINT = "https://nominatim.openstreetmap.org/search"
PAUSE = 1.1

GOOD_PLACE = {"city", "town", "village", "hamlet", "suburb", "borough",
              "municipality", "locality", "isolated_dwelling", "quarter",
              "neighbourhood", "county", "state", "province", "region",
              "administrative", "island", "farm"}

def fold(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()

def _get(q):
    url = ENDPOINT + "?" + urllib.parse.urlencode(
        {"q": q, "format": "jsonv2", "limit": 5, "addressdetails": 0})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def _rank(hits, want):
    """A populated place beats a boundary beats anything else; then importance."""
    def key(h):
        cat, typ = h.get("category"), h.get("type")
        tier = 0 if (cat == "place" and typ in GOOD_PLACE) else \
               1 if (cat == "boundary" and typ in GOOD_PLACE) else 2
        named = 0 if want and want in fold(h.get("display_name", "")) else 1
        return (tier, named, -float(h.get("importance") or 0))
    return sorted(hits, key=key)

def geocode(name, cache, sleeper=time.sleep):
    key = fold(name)
    if key in cache:
        return cache[key]
    parts = [p.strip() for p in str(name).split(",") if p.strip()]
    want = fold(parts[0]) if parts else ""
    # whole string first, then drop leading detail (street, church, farm)
    attempts = [", ".join(parts[i:]) for i in range(0, max(1, len(parts) - 1))]
    for i, q in enumerate(attempts):
        try:
            hits = _get(q)
        except Exception as e:
            sys.stderr.write(f"  ! {q}: {type(e).__name__} {e}\n")
            hits = []
        sleeper(PAUSE)
        if not hits:
            continue
        h = _rank(hits, want)[0]
        cat, typ = h.get("category"), h.get("type")
        solid = (cat in ("place", "boundary") and typ in GOOD_PLACE
                 and want and want in fold(h.get("display_name", "")))
        rec = {"lat": round(float(h["lat"]), 5), "lon": round(float(h["lon"]), 5),
               "matched": h.get("display_name", ""), "kind": f"{cat}/{typ}",
               "conf": "exact" if (solid and i == 0) else "approx",
               "asked": name, "via": q}
        cache[key] = rec
        return rec
    cache[key] = None
    return None

# ---- reading the cache back, which is what the archives actually do --------

def load(path=None):
    """The shared gazetteer, as a dict keyed on the folded place name."""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "gazetteer.json")
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}

def find(name, gaz):
    """A coordinate for this name, or None.

    Tries the whole string, then drops leading segments — the same ladder the
    lookup itself climbed, so a place recorded as "St Mary's, Limerick" finds
    the Limerick entry that was cached under the shorter form.
    """
    if not name:
        return None
    parts = [x.strip() for x in str(name).split(",") if x.strip()]
    for i in range(len(parts)):
        hit = gaz.get(fold(", ".join(parts[i:])))
        if hit:
            return hit
    return gaz.get(fold(parts[0])) if parts else None


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", required=True, help="JSON file: a list of place names")
    ap.add_argument("--cache", required=True, help="the shared gazetteer, read and written")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    cache = json.load(open(a.cache, encoding="utf-8")) if os.path.exists(a.cache) else {}
    names = json.load(open(a.names, encoding="utf-8"))
    todo = [n for n in names if fold(n) not in cache]
    if a.limit:
        todo = todo[:a.limit]
    print(f"geocode: {len(names)} names, {len(names)-len(todo)} already cached, {len(todo)} to ask")
    for i, n in enumerate(todo, 1):
        r = geocode(n, cache)
        print(f"  [{i}/{len(todo)}] {n[:48]:<48} {'MISS' if not r else r['conf']+' '+str(r['lat'])+','+str(r['lon'])}")
        if i % 25 == 0:
            json.dump(cache, open(a.cache, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    json.dump(cache, open(a.cache, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    hit = sum(1 for v in cache.values() if v)
    print(f"geocode: cache now holds {len(cache)} names, {hit} resolved, {len(cache)-hit} unresolved")

if __name__ == "__main__":
    sys.exit(main())

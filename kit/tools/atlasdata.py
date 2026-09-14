#!/usr/bin/env python3
"""Turn an archive's places into the JSON the kit's Atlas reads.

Each archive shapes its places differently — one keeps counts, one keeps slugs,
one keeps a paragraph — so the mapping stays in the archive. What is shared is
everything after the mapping: finding the coordinate in the estate gazetteer,
dropping what has none, counting what was dropped, and writing the file.

A place with no coordinate is not an error and is not silently lost: it is
counted and reported, because "46 of 51 are on the map" is a fact a reader is
entitled to and a number the page should print rather than imply.
"""
import json, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geocode as G


def slug(name):
    """A stable URL for a place, from the name the archive prints.

    Places get a page of their own on four of the seven archives and not on the
    other three, so the atlas offers "the page that proves it" and half the
    estate has nothing behind the link. A slug here means the page can be built
    from the same data the marker is, rather than from a second list that would
    drift away from the first.
    """
    t = unicodedata.normalize("NFD", str(name or "")).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t or "place"


def build(rows, out_path, gaz=None, quiet=False, countries=None):
    """rows: dicts already in Atlas shape but carrying `_lookup` instead of lat/lon."""
    gaz = G.load() if gaz is None else gaz
    places, missed, approx, outside = [], [], 0, []
    for r in rows:
        hit = G.find(r.pop("_lookup", r.get("name")), gaz)
        if not hit:
            missed.append(r.get("name"))
            continue
        # A dot in the wrong country is worse than no dot: "Rijeka" resolved
        # to Bosnia and "Transvaal" to a street in Germany before this. An
        # archive names the countries it can plausibly be in, and anything
        # landing outside them is refused and reported rather than drawn.
        if countries and not any(c.lower() in hit["matched"].lower() for c in countries):
            outside.append(f"{r.get('name')} -> {hit['matched'].split(',')[-1].strip()}")
            continue
        if hit["conf"] != "exact":
            approx += 1
        r["lat"], r["lon"] = hit["lat"], hit["lon"]
        r.setdefault("slug", slug(r.get("name")))
        # a coordinate is a claim; say how sure it is, and where it came from
        r["fix"] = hit["conf"]
        places.append(r)
    seen = {}
    for r in places:
        base = r["slug"]; n = seen.get(base, 0) + 1; seen[base] = n
        if n > 1:
            r["slug"] = f"{base}-{n}"
        # the marker's "page that proves it" — set after the slug is final
        r.setdefault("href", f"/places/{r['slug']}/")
    stats = {"places": len(places),
             "withPeople": sum(1 for p in places if p.get("n")),
             "people": sum(p.get("n") or 0 for p in places),
             "unplaced": len(missed) + len(outside), "approx": approx}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump({"places": places, "stats": stats},
              open(out_path, "w", encoding="utf-8"), ensure_ascii=False)
    if not quiet:
        print(f"atlas: {len(places)} placed ({approx} approximate), "
              f"{len(missed)} without a coordinate, {stats['people']} people placed")
        if outside:
            print("       REFUSED, outside the expected countries: " + "; ".join(outside[:6]))
        if missed:
            print("       unplaced: " + ", ".join(str(m) for m in missed[:8])
                  + (" …" if len(missed) > 8 else ""))
    return stats

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
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geocode as G


def build(rows, out_path, gaz=None, quiet=False):
    """rows: dicts already in Atlas shape but carrying `_lookup` instead of lat/lon."""
    gaz = G.load() if gaz is None else gaz
    places, missed, approx = [], [], 0
    for r in rows:
        hit = G.find(r.pop("_lookup", r.get("name")), gaz)
        if not hit:
            missed.append(r.get("name"))
            continue
        if hit["conf"] != "exact":
            approx += 1
        r["lat"], r["lon"] = hit["lat"], hit["lon"]
        # a coordinate is a claim; say how sure it is, and where it came from
        r["fix"] = hit["conf"]
        places.append(r)
    stats = {"places": len(places),
             "withPeople": sum(1 for p in places if p.get("n")),
             "people": sum(p.get("n") or 0 for p in places),
             "unplaced": len(missed), "approx": approx}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump({"places": places, "stats": stats},
              open(out_path, "w", encoding="utf-8"), ensure_ascii=False)
    if not quiet:
        print(f"atlas: {len(places)} placed ({approx} approximate), "
              f"{len(missed)} without a coordinate, {stats['people']} people placed")
        if missed:
            print("       unplaced: " + ", ".join(str(m) for m in missed[:8])
                  + (" …" if len(missed) > 8 else ""))
    return stats
